// WebSocket Connection Manager
class WebSocketManager {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.baseReconnectDelay = 1000; // Start with 1 second
        this.maxReconnectDelay = 30000; // Cap at 30 seconds
        
        // Bind methods
        this.connect = this.connect.bind(this);
        this.handleReconnect = this.handleReconnect.bind(this);
        
        // Handle online/offline status
        window.addEventListener('online', () => {
            console.log('Network restored. Reconnecting WebSocket...');
            this.reconnectAttempts = 0;
            this.connect();
        });
        
        window.addEventListener('offline', () => {
            console.log('Network lost. Pausing WebSocket reconnection.');
            if (this.socket) {
                this.socket.close();
            }
        });

        this.connect();
        WebSocketManager.initGlobalToast();
    }

    connect() {
        if (!navigator.onLine) {
             console.log('Offline. Waiting for network...');
             return;
        }

        // Check if user is logged in
        const userId = document.body.dataset.userId;
        if (!userId || userId === "None" || userId === "") {
            console.log('User not logged in. Skipping WebSocket connection.');
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/user/`;

        console.log(`Connecting to WebSocket at ${wsUrl}`);
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            window.dispatchEvent(new Event('websocket:connected'));
        };

        this.socket.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                this.handleMessage(data);
            } catch (err) {
                console.error('Error parsing WebSocket message:', err);
            }
        };

        this.socket.onclose = (e) => {
            console.log('WebSocket disconnected', e.reason);
            // Only reconnect if not closed cleanly
            if (!e.wasClean) {
                this.handleReconnect();
            }
        };

        this.socket.onerror = (e) => {
            console.error('WebSocket error:', e);
            this.socket.close();
        };
    }

    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            // Calculate exponential backoff delay with jitter
            const delay = Math.min(
                this.baseReconnectDelay * Math.pow(1.5, this.reconnectAttempts), 
                this.maxReconnectDelay
            );
            
            // Add slight randomness to prevent thundering herd
            const jitter = Math.random() * 1000; 
            const finalDelay = delay + jitter;

            this.reconnectAttempts++;
            console.log(`Reconnecting attempt ${this.reconnectAttempts} in ${Math.round(finalDelay)}ms...`);
            
            setTimeout(this.connect, finalDelay);
        } else {
            console.error('Max reconnect attempts reached. Please refresh the page.');
            this.showNotification({
                title: 'Connection Lost',
                body: 'Please refresh the page to reconnect.',
                type: 'error'
            });
        }
    }

    handleMessage(data) {
        console.log('WS Message:', data.type, data);
        
        console.log(`Processing message type: ${data.type}`);
        switch (data.type) {
            case 'notification':
                this.showNotification(data.notification);
                this.updateUnreadCount(data.unread_count);
                window.dispatchEvent(new CustomEvent('notificationReceived', { detail: data }));
                break;
            
            case 'token_update': 
                this.updateTokenBalance(data.balance);
                window.dispatchEvent(new CustomEvent('tokenUpdated', { detail: data }));
                break;
            
            case 'status_update':
                this.handleStatusUpdate(data);
                this.updateUnreadCount(data.unread_count);
                // handleStatusUpdate already dispatches 'bookingStatusChanged'
                break;
            
            case 'new_booking_request':
                if (data.role === 'provider' || !data.role) { 
                     this.incrementCounter('dashboard-incoming-count');
                }
                window.dispatchEvent(new CustomEvent('newBookingRequest', { detail: data }));
                this.showNotification({title: 'New Booking', body: 'You received a new booking request!', link: '/meetings/'});
                break;

            case 'new_swap_request':
                this.incrementCounter('dashboard-swap-count');
                window.dispatchEvent(new CustomEvent('newSwapRequest', { detail: data }));
                this.showNotification({title: 'New Swap Request', body: 'Someone wants to swap skills with you!', link: '/skills/manage-requests/'});
                break;
                
            case 'notification_history':
                this.updateUnreadCount(data.unread_count);
                window.dispatchEvent(new CustomEvent('notificationHistoryReceived', { detail: data }));
                break;
                
            case 'unread_count_update':
                this.updateUnreadCount(data.count);
                window.dispatchEvent(new CustomEvent('unreadCountUpdated', { detail: data }));
                break;
                
            case 'force_logout':
                alert(data.message || 'You have been logged out.');
                window.location.href = '/accounts/logout/';
                break;
        }
    }

    showNotification(notification) {
        // Map notification format to toast format
        window.showGlobalToast({
            title: notification.title,
            body: notification.body,
            link: notification.link,
            type: 'info' // Default type
        });
    }

    // Global Toast Function
    static initGlobalToast() {
        window.showGlobalToast = function(notif) {
            let container = document.getElementById('toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                container.style.cssText = 'position:fixed; top:80px; right:20px; z-index:10500;';
                document.body.appendChild(container);
            }

            container.innerHTML = ''; // Single toast policy

            const isDarkMode = document.body.classList.contains('dark-mode');
            const bgStyle = isDarkMode ? 'background: #1e1e1e; color: #f5f5f5;' : 'background: white; color: #000;';
            const textClass = isDarkMode ? 'text-light' : 'text-dark';
            const btnCloseClass = isDarkMode ? 'btn-close-white' : '';
            
            let borderColor = '#f9b934';
            let btnColor = 'btn-warning';

            if (notif.type === 'error') {
                borderColor = '#ef4444';
                btnColor = 'btn-danger';
            } else if (notif.type === 'success') {
                borderColor = '#10b981';
                btnColor = 'btn-success';
            }

            const id = 'toast-' + Date.now();
            const html = `
                <div id="${id}" class="toast show animate__animated animate__fadeInRight" style="${bgStyle} border-left: 5px solid ${borderColor}; margin-bottom: 10px; width: 300px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                    <div class="toast-header border-0 bg-transparent">
                        <strong class="me-auto ${textClass}">${notif.title}</strong>
                        <button type="button" class="btn-close ${btnCloseClass}" onclick="document.getElementById('${id}').remove()"></button>
                    </div>
                    <div class="toast-body ${textClass} pt-0">
                        ${notif.body}
                        ${notif.link ? `<hr class="my-2" style="border-color: ${isDarkMode ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.1)'}"><a href="${notif.link}" class="btn btn-sm ${btnColor} w-100 fw-bold">View Details</a>` : ''}
                    </div>
                </div>`;

            container.insertAdjacentHTML('beforeend', html);

            setTimeout(() => {
                const t = document.getElementById(id);
                if (t) {
                    t.classList.replace('animate__fadeInRight', 'animate__fadeOutRight');
                    setTimeout(() => t.remove(), 1000);
                }
            }, 5000);
        };
    }

    updateUnreadCount(count) {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            badge.textContent = count;
            if (count > 0) {
                badge.classList.remove('d-none');
            } else {
                badge.classList.add('d-none');
            }
        }
    }

    incrementCounter(elementId) {
        console.log(`Attempting to increment counter: ${elementId}`);
        const el = document.getElementById(elementId);
        if (el) {
            let currentText = el.innerText;
            console.log('Current text:', currentText);
            let count = parseInt(currentText) || 0;
            console.log('Parsed count:', count);
            el.innerText = count + 1;
            console.log('New count set to:', count + 1);
            
            
            el.classList.add('animate__animated', 'animate__pulse');
            setTimeout(() => el.classList.remove('animate__animated', 'animate__pulse'), 1000);
        } else {
             console.error(`Element with ID ${elementId} NOT found in DOM`);
        }
    }

    updateTokenBalance(balance) {
        
        const dashboardBalance = document.getElementById('dashboard-token-balance');
        if (dashboardBalance) {
            dashboardBalance.innerText = balance;
             dashboardBalance.classList.add('animate__animated', 'animate__pulse');
             setTimeout(() => dashboardBalance.classList.remove('animate__animated', 'animate__pulse'), 1000);
        }

        
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            if (link.textContent.includes('Tokens')) {
                
                const span = link.querySelector('.nav-underline');
                link.innerHTML = `Tokens ${balance} ${span ? span.outerHTML : ''}`;
            }
        });
    }

    handleStatusUpdate(data) {
        
        this.showNotification({
            title: 'Booking Update',
            body: data.message,
            link: '/meetings/' 
        });

        
        window.dispatchEvent(new CustomEvent('bookingStatusChanged', { detail: data }));
    }
}


document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('notificationBell')) {
        window.webSocketManager = new WebSocketManager();
    }
});

// Initialize global toast immediately so it's available for Django messages
WebSocketManager.initGlobalToast();
