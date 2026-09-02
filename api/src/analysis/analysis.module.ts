import { AnalysisController } from './analysis.controller';
import { AnalysisGateway } from './analysis.gateway';
import { AnalysisService } from './analysis.service';
import { Module } from '@nestjs/common';

@Module({
  imports: [],
  controllers: [AnalysisController],
  providers: [AnalysisService, AnalysisGateway],
})
export class AnalysisModule {}
