// WebSocket Connection Manager
class WebSocketManager {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 3000; // 3 seconds
        this.connect();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/user/`;

        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            window.dispatchEvent(new Event('websocket:connected'));
        };

        this.socket.onmessage = (e) => {
            const data = JSON.parse(e.data);
            this.handleMessage(data);
        };

        this.socket.onclose = (e) => {
            console.log('WebSocket disconnected', e.reason);
            this.handleReconnect();
        };

        this.socket.onerror = (e) => {
            console.error('WebSocket error:', e);
            this.socket.close();
        };
    }

    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting attempt ${this.reconnectAttempts}...`);
            setTimeout(() => this.connect(), this.reconnectInterval);
        } else {
            console.error('Max reconnect attempts reached');
        }
    }

    handleMessage(data) {
        console.log('WS Message:', data.type, data);
        
        console.log(`Processing message type: ${data.type}`);
        switch (data.type) {
            case 'notification':
                this.showNotification(data.notification);
                this.updateUnreadCount(data.unread_count);
                break;
            
            case 'token_update': 
                this.updateTokenBalance(data.balance);
                break;
            
            case 'status_update':
                this.handleStatusUpdate(data);
                this.updateUnreadCount(data.unread_count);
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
                this.showNotification({title: 'New Swap Request', body: 'Someone wants to swap skills with you!', link: '/skills/manage-requests/'});
                break;
                
            case 'notification_history':
                this.updateUnreadCount(data.unread_count);
                break;
                
            case 'unread_count_update':
                this.updateUnreadCount(data.count);
                break;
                
            case 'force_logout':
                alert(data.message || 'You have been logged out.');
                window.location.href = '/accounts/logout/';
                break;
        }
    }

    showNotification(notification) {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.style.cssText = 'position:fixed; top:80px; right:20px; z-index:10500;';
            document.body.appendChild(container);
        }


        container.innerHTML = '';

        const isDarkMode = document.body.classList.contains('dark-mode');
        const bgStyle = isDarkMode ? 'background: #1e1e1e; color: #f5f5f5;' : 'background: white; color: #000;';
        const textClass = isDarkMode ? 'text-light' : 'text-dark';
        const btnCloseClass = isDarkMode ? 'btn-close-white' : '';
        const id = 'toast-' + Date.now();

        const html = `
            <div id="${id}" class="toast show animate__animated animate__fadeInRight" style="${bgStyle} border-left: 5px solid #f9b934; margin-bottom: 10px; width: 300px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                <div class="toast-header border-0 bg-transparent">
                    <strong class="me-auto ${textClass}">${notification.title}</strong>
                    <button type="button" class="btn-close ${btnCloseClass}" onclick="document.getElementById('${id}').remove()"></button>
                </div>
                <div class="toast-body ${textClass} pt-0">
                    ${notification.body}
                    ${notification.link ? `<hr class="my-2" style="border-color: ${isDarkMode ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.1)'}"><a href="${notification.link}" class="btn btn-sm btn-warning w-100 fw-bold">View Details</a>` : ''}
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
