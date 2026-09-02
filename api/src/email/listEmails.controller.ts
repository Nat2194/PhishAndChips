import { ListEmailsService } from './listEmails.service';
import { Controller, Get, Post, Body, Header } from '@nestjs/common';

@Controller('mail')
export class ListEmailsController {
  constructor(private readonly listEmailsService: ListEmailsService) {}

  @Get()
  //@Header('Access-Control-Allow-Origin', 'http://localhost:8080')
  //@Header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
  //@Header('Access-Control-Allow-Credentials', 'true')
  async obtainEmailsToAnalyze() {
    return this.listEmailsService.obtainEmails();
  }
}

