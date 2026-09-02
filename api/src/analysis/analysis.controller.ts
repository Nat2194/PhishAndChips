import {
  Controller,
  Post,
  Body,
  Header,
  Inject,
  Options,
} from '@nestjs/common';
import { WebSocketServer } from '@nestjs/websockets';
import { Server } from 'socket.io';
import { AnalysisService } from './analysis.service';
import { AnalysisGateway } from './analysis.gateway';

@Controller('/analysis')
export class AnalysisController {
  constructor(
    private readonly analysisService: AnalysisService,
    @Inject(AnalysisGateway)
    private readonly webSocketServerService: AnalysisGateway,
  ) {}

  @Post('/socket')
  @Header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
  @Header('Access-Control-Allow-Origin', 'http://localhost:8080')
  @Header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
  @Header('Access-Control-Allow-Credentials', 'true')
  async createSocketServer(@Body() data: { mailUid: string }) {
    console.log('create server');
    const { mailUid } = data;
    const port = await this.webSocketServerService.createServer(mailUid);
    console.log(`on port :${port}`);
    return { port };
  }

  @Options('/socket') // Ajoutez cette méthode pour gérer les requêtes OPTIONS pour /socket
  @Header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
  @Header('Access-Control-Allow-Origin', 'http://localhost:8080')
  @Header('Access-Control-Allow-Methods', 'GET, POST')
  @Header('Access-Control-Allow-Credentials', 'true')
  async handleSocketOptions() {
    return 'OK';
  }

  @Post('/run')
  @Header('Access-Control-Allow-Origin', 'http://localhost:8080')
  @Header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
  @Header('Access-Control-Allow-Credentials', 'true')
  async analyseEmail(@Body() data: { mailUid: string; port: number }) {
    const { mailUid, port } = data;

    await new Promise((resolve) => setTimeout(resolve, 1000)); // Wait for the server to start listening

    const verdict = await this.analysisService.analyse(mailUid, port);

    this.webSocketServerService.getServer(mailUid)?.emit('verdict', verdict);

    return verdict;
  }

  @Post('/cleanup')
  @Header('Access-Control-Allow-Origin', 'http://localhost:8080')
  @Header('Access-Control-Allow-Methods', 'POST')
  @Header('Access-Control-Allow-Credentials', 'true')
  async cleanup() {
    // Close all WebSocket servers
    const mailUids = this.webSocketServerService.getMailUids();
    for (const mailUid of mailUids) {
      const server = this.webSocketServerService.getServer(mailUid);
      if (server) {
        await server.close();
      }
    }

    this.webSocketServerService.clearServers();

    return 'Cleanup completed';
  }
}
