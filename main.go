package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"os"
	"sync"
	"time"
)

// ConnectionLog represents a log entry for a connection
type ConnectionLog struct {
	Timestamp string `json:"timestamp"`
	Protocol  string `json:"protocol"`
	IP        string `json:"ip"`
	Data      string `json:"data"`
}

// ProtocolHandler represents a function that handles a specific protocol
type ProtocolHandler func(net.Conn)

func main() {
	// Define the ports and their respective protocol handlers
	protocols := map[int]ProtocolHandler{
		// 22:   handleSSH,
		80:    handleHTTP,
		443:   handleHTTPS,
		3389:  handleRDP,
		21:    handleFTP,
		25:    handleSMTP,
		110:   handlePOP3,
		143:   handleIMAP,
		23:    handleTelnet,
		3306:  handleMySQL,
		6379:  handleRedis,
		389:   handleLDAP,
		27017: handleMongo,
	}

	var wg sync.WaitGroup

	// Start a goroutine for each protocol
	for port, handler := range protocols {
		wg.Add(1)
		go func(p int, h ProtocolHandler) {
			defer wg.Done()
			startListener(p, h)
		}(port, handler)
	}

	// Keep the main thread alive
	wg.Wait()
}

// startListener starts a listener on the specified port
func startListener(port int, handler ProtocolHandler) {
	listener, err := net.Listen("tcp", fmt.Sprintf("0.0.0.0:%d", port))
	if err != nil {
		log.Fatalf("Failed to bind to port %d: %v", port, err)
	}
	defer listener.Close()

	fmt.Printf("Listening on port %d...\n", port)

	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("Failed to establish connection on port %d: %v", port, err)
			continue
		}

		go func() {
			handler(conn)
		}()
	}
}

// logConnection logs connection details to a file
func logConnection(protocol, ip string, data []byte) {
	logEntry := ConnectionLog{
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Protocol:  protocol,
		IP:        ip,
		Data:      string(data),
	}

	logEntryJSON, err := json.Marshal(logEntry)
	if err != nil {
		log.Printf("Failed to serialize log entry: %v", err)
		return
	}

	file, err := os.OpenFile("honeypot.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		log.Printf("Failed to open log file: %v", err)
		return
	}
	defer file.Close()

	if _, err := file.WriteString(string(logEntryJSON) + "\n"); err != nil {
		log.Printf("Failed to write to log file: %v", err)
	} else {
		fmt.Printf("Logged %s data from %s\n", protocol, ip)
	}
}

// Protocol Handlers
func handleSSH(conn net.Conn) {
	logAndReply(conn, "SSH", "SSH-2.0-OpenSSH_7.4\r\n")
}

func handleHTTP(conn net.Conn) {
	logAndReply(conn, "HTTP", "HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
}

func handleHTTPS(conn net.Conn) {
	logAndReply(conn, "HTTPS", "Fake HTTPS Handshake")
}

func handleRDP(conn net.Conn) {
	logAndReply(conn, "RDP", "Fake RDP Handshake")
}

func handleFTP(conn net.Conn) {
	logAndReply(conn, "FTP", "220 (Fake FTP Server)\r\n")
}

func handleSMTP(conn net.Conn) {
	logAndReply(conn, "SMTP", "220 Fake SMTP Server Ready\r\n")
}

func handlePOP3(conn net.Conn) {
	logAndReply(conn, "POP3", "+OK Fake POP3 Server Ready\r\n")
}

func handleIMAP(conn net.Conn) {
	logAndReply(conn, "IMAP", "* OK Fake IMAP Server Ready\r\n")
}

func handleTelnet(conn net.Conn) {
	logAndReply(conn, "Telnet", "Welcome to the Fake Telnet Server\r\n")
}

func handleMySQL(conn net.Conn) {
	logAndReply(conn, "MySQL", "5.7.0 Fake MySQL Server Greeting")
}

func handleRedis(conn net.Conn) {
	logAndReply(conn, "Redis", "-ERR Fake Redis Server\r\n")
}

func handleLDAP(conn net.Conn) {
	logAndReply(conn, "LDAP", "Fake LDAP Server Ready\r\n")
}

func handleMongo(conn net.Conn) {
	logAndReply(conn, "MongoDB", "Fake MongoDB Server Response")
}

// logAndReply is a generic function to log and reply
func logAndReply(conn net.Conn, protocol, response string) {
	defer conn.Close()

	peerAddr := conn.RemoteAddr().String()
	fmt.Printf("%s connection from: %s\n", protocol, peerAddr)

	// Read data from connection
	buffer := make([]byte, 4096)
	size, err := conn.Read(buffer)
	if err != nil && err != io.EOF {
		log.Printf("Failed to read from %s connection: %v", protocol, err)
		size = 0
	}

	logConnection(protocol, peerAddr, buffer[:size])

	// Write response
	writer := bufio.NewWriter(conn)
	_, err = writer.WriteString(response)
	if err != nil {
		log.Printf("Failed to write response to %s: %v", protocol, err)
		return
	}
	writer.Flush()
}
