import { ListEmailsService } from './listEmails.service';
import { ListEmailsController } from './listEmails.controller';

import { Module } from '@nestjs/common';

@Module({
  imports: [],
  controllers: [ListEmailsController],
  providers: [ListEmailsService],
})
export class ListEmailsModule {}
