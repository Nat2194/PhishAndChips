import { NestFactory } from '@nestjs/core';

// Custom imports
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableCors({
    origin: 'http://localhost:8080',
    credentials: true,
    optionsSuccessStatus: 200,
  });
  await app.listen(3000);
}
bootstrap();
