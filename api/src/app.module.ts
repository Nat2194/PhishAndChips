import { Module } from '@nestjs/common';

// Custom imports
import { AppService } from './app.service';
import { AppController } from './app.controller';
import { AnalysisModule } from './analysis/analysis.module';
import { ListEmailsModule } from './email/listEmails.module';

@Module({
  imports: [AnalysisModule, ListEmailsModule],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
