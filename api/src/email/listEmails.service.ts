import { Injectable } from '@nestjs/common';
import { Email } from '../types/email.interface';
import { retrieveEmails } from './list-emails';

@Injectable()
export class ListEmailsService {
  async obtainEmails(): Promise<Email[]> {
    const ListEmails = retrieveEmails();
    return ListEmails;
  }
}
