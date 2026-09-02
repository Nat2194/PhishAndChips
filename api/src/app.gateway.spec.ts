import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import { AppGateway } from './app.gateway';
import * as WebSocket from 'ws';

describe('AppGateway', () => {
  let app: INestApplication;
  let appGateway: AppGateway;
  let wss: WebSocket.Server;

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      providers: [AppGateway],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();

    appGateway = moduleFixture.get<AppGateway>(AppGateway);
    const httpServer = app.getHttpServer();

    // Créer un serveur WebSocket pour effectuer les tests
    const wss = new WebSocket.Server({ noServer: true });

    httpServer.on('upgrade', (request, socket, head) => {
      wss.handleUpgrade(request, socket, head, (ws) => {
        wss.emit('connection', ws, request);
      });
    });
  });

  afterAll(async () => {
    await app.close();
    wss.close();
  });

  it('should handle connection', () => {
    // Simuler une connexion d'un client WebSocket
    const ws = new WebSocket('ws://localhost:5000');
    expect(appGateway.handleConnection).toHaveBeenCalled();
  });

  it('should handle disconnection', () => {
    // Simuler une déconnexion d'un client WebSocket
    const ws = new WebSocket('ws://localhost:5000');
    ws.close();
    expect(appGateway.handleDisconnect).toHaveBeenCalled();
  });

  it('should handle events', (done) => {
    // Simuler l'envoi d'un message 'events' à partir d'un client WebSocket
    const ws = new WebSocket('ws://localhost:5000');
    ws.on('open', () => {
      ws.send(JSON.stringify({ event: 'events', data: 'Hello' }));
    });
    ws.on('message', (data) => {
      expect(data).toBe('Hello');
      done();
    });
  });
});

