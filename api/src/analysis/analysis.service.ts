import { Injectable } from '@nestjs/common';
import { analyseMail } from './analysis';

@Injectable()
export class AnalysisService {
  async analyse(mailUid: string, port: number): Promise<string> {
    console.log(`analysing on port ${port}`);
    return analyseMail(mailUid, port);
  }
}
