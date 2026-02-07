import socket
import ssl

def test_connection(host, port, use_ssl=False):
    print(f"\n--- Testing connection to {host}:{port} (SSL={use_ssl}) ---")
    try:
        # Resolve IP first to see if DNS works and what IP (v4/v6) it picks
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        print(f"DNS Resolution IPs: {[info[4][0] for info in infos]}")
        
        # Try connecting
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        if use_ssl:
            context = ssl.create_default_context()
            sock = context.wrap_socket(sock, server_hostname=host)
            
        sock.connect((host, port))
        print("✅ Connection SUCCESSFUL!")
        sock.close()
    except Exception as e:
        print(f"❌ Connection FAILED: {e}")

print("Running Connectivity Tests...")
test_connection('smtp.gmail.com', 587, use_ssl=False)
test_connection('smtp.gmail.com', 465, use_ssl=True)
test_connection('google.com', 80, use_ssl=False) # Control test
