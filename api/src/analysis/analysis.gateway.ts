import { Injectable } from '@nestjs/common';
import { createServer, Server } from 'http';
import { Server as SocketIOServer, Socket } from 'socket.io';

@Injectable()
export class AnalysisGateway {
  private servers: Map<string, Server> = new Map<string, Server>();
  private ports: Map<string, number> = new Map<string, number>();
  private sockets: Map<string, Socket[]> = new Map<string, Socket[]>();

  public createServer(mailUid: string): number {
    const startPort = 5000;
    const endPort = 6000;
    console.log('ports list:');
    this.ports.forEach((port, mailUid) => {
      console.log(`mailUid: ${mailUid}, port: ${port}`);
    });

    if (this.ports.size >= 2) {
      throw new Error('Maximum number of active ports reached');
    }

    for (let port = startPort; port <= endPort; port++) {
      console.log(`port : ${port}`);
      if (!Array.from(this.ports.values()).includes(port)) {
        const server = createServer();
        const io = new SocketIOServer(server, {
          cors: {
            origin: 'http://localhost:8080',
            methods: ['GET', 'POST', 'OPTIONS'],
            credentials: true,
          },
        });

        io.on('connection', (socket: Socket) => {
          console.log('Socket is live');
          if (!this.sockets.has(mailUid)) {
            this.sockets.set(mailUid, []);
          }
          this.sockets.get(mailUid)?.push(socket);

          socket.on('status', (status: string) => {
            console.log('Received status:', status);
            this.emitStatus(mailUid, status);
          });
        });

        server.on('request', (req, res) => {
          if (req.method === 'OPTIONS') {
            // Handle OPTIONS request separately
            res.writeHead(200);
            res.end();
          }
        });

        server.listen(port, () => {
          console.log(
            `WebSocket server for mail ${mailUid} is running on port ${port}`,
          );
        });

        this.servers.set(mailUid, server);
        this.ports.set(mailUid, port);
        return this.ports.get(mailUid);
      }
    }

    throw new Error(`Unable to find an available port for mail ${mailUid}`);
  }

  public getServer(mailUid: string): Server | undefined {
    return this.servers.get(mailUid);
  }

  public getPort(mailUid: string): number | undefined {
    return this.ports.get(mailUid);
  }

  public getMailUids(): string[] {
    return Array.from(this.servers.keys());
  }

  public clearServers(): void {
    for (const server of this.servers.values()) {
      server.close();
    }
    this.servers.clear();
    this.ports.clear();
    this.sockets.clear();
  }

  public emitStatus(mailUid: string, status: string): void {
    const sockets = this.sockets.get(mailUid);
    if (sockets) {
      for (const socket of sockets) {
        socket.emit('status', status);
      }
    }
  }
}
