use chrono::Utc;
use serde_json::json;
use std::fs::OpenOptions;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

fn main() {
    // Define the ports and their respective protocol handlers
    let protocols: Vec<(u16, fn(TcpStream))> = vec![
        //(22, handle_ssh as fn(TcpStream)),
        (80, handle_http as fn(TcpStream)),
        (443, handle_https as fn(TcpStream)),
        (3389, handle_rdp as fn(TcpStream)),
        (21, handle_ftp as fn(TcpStream)),
        (25, handle_smtp as fn(TcpStream)),
        (110, handle_pop3 as fn(TcpStream)),
        (143, handle_imap as fn(TcpStream)),
        (23, handle_telnet as fn(TcpStream)),
        (3306, handle_mysql as fn(TcpStream)),
        (6379, handle_redis as fn(TcpStream)),
        (389, handle_ldap as fn(TcpStream)),
        (27017, handle_mongo as fn(TcpStream)),
    ];

    // Start a thread for each protocol
    for (port, handler) in protocols {
        thread::spawn(move || {
            start_listener(port, handler);
        });
    }

    // Keep the main thread alive
    loop {
        thread::park();
    }
}

// Start a listener on the specified port
fn start_listener(port: u16, handler: fn(TcpStream)) {
    let listener = TcpListener::bind(format!("0.0.0.0:{}", port))
        .unwrap_or_else(|_| panic!("Failed to bind to port {}", port));

    println!("Listening on port {}...", port);

    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                thread::spawn(move || {
                    handler(stream);
                });
            }
            Err(e) => {
                eprintln!("Failed to establish connection on port {}: {}", port, e);
            }
        }
    }
}

// Log connection details
fn log_connection(protocol: &str, ip: String, data: &[u8]) {
    let log_entry = json!({
        "timestamp": Utc::now().to_rfc3339(),
        "protocol": protocol,
        "ip": ip,
        "data": String::from_utf8_lossy(data)
    });

    let log_entry_str = match serde_json::to_string(&log_entry) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Failed to serialize log entry: {}", e);
            return;
        }
    };

    let mut file = match OpenOptions::new()
        .create(true)
        .append(true)
        .open("honeypot.log")
    {
        Ok(file) => file,
        Err(e) => {
            eprintln!("Failed to open log file: {}", e);
            return;
        }
    };

    if let Err(e) = writeln!(file, "{}", log_entry_str) {
        eprintln!("Failed to write to log file: {}", e);
    } else {
        println!("Logged {} data from {}", protocol, ip);
    }
}

// Protocol Handlers
fn handle_ssh(mut stream: TcpStream) {
    log_and_reply(&mut stream, "SSH", "SSH-2.0-OpenSSH_7.4\r\n");
}

fn handle_http(mut stream: TcpStream) {
    log_and_reply(
        &mut stream,
        "HTTP",
        "HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n",
    );
}

fn handle_https(mut stream: TcpStream) {
    log_and_reply(&mut stream, "HTTPS", "Fake HTTPS Handshake");
}

fn handle_rdp(mut stream: TcpStream) {
    log_and_reply(&mut stream, "RDP", "Fake RDP Handshake");
}

fn handle_ftp(mut stream: TcpStream) {
    log_and_reply(&mut stream, "FTP", "220 (Fake FTP Server)\r\n");
}

fn handle_smtp(mut stream: TcpStream) {
    log_and_reply(&mut stream, "SMTP", "220 Fake SMTP Server Ready\r\n");
}

fn handle_pop3(mut stream: TcpStream) {
    log_and_reply(&mut stream, "POP3", "+OK Fake POP3 Server Ready\r\n");
}

fn handle_imap(mut stream: TcpStream) {
    log_and_reply(&mut stream, "IMAP", "* OK Fake IMAP Server Ready\r\n");
}

fn handle_telnet(mut stream: TcpStream) {
    log_and_reply(
        &mut stream,
        "Telnet",
        "Welcome to the Fake Telnet Server\r\n",
    );
}

fn handle_mysql(mut stream: TcpStream) {
    log_and_reply(&mut stream, "MySQL", "5.7.0 Fake MySQL Server Greeting");
}

fn handle_redis(mut stream: TcpStream) {
    log_and_reply(&mut stream, "Redis", "-ERR Fake Redis Server\r\n");
}

fn handle_ldap(mut stream: TcpStream) {
    log_and_reply(&mut stream, "LDAP", "Fake LDAP Server Ready\r\n");
}

fn handle_mongo(mut stream: TcpStream) {
    log_and_reply(&mut stream, "MongoDB", "Fake MongoDB Server Response");
}

// Generic function to log and reply
fn log_and_reply(stream: &mut TcpStream, protocol: &str, response: &str) {
    let peer_addr = match stream.peer_addr() {
        Ok(addr) => addr,
        Err(e) => {
            eprintln!("Failed to get peer address: {}", e);
            return;
        }
    };
    println!("{} connection from: {}", protocol, peer_addr);

    let mut buffer = [0; 4096];
    let size = match stream.read(&mut buffer) {
        Ok(size) => size,
        Err(e) => {
            eprintln!("Failed to read from {} connection: {}", protocol, e);
            0
        }
    };

    log_connection(protocol, peer_addr.to_string(), &buffer[..size]);

    if let Err(e) = stream.write_all(response.as_bytes()) {
        eprintln!("Failed to write response to {}: {}", protocol, e);
    }
}
