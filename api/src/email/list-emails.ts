import { exec } from 'child_process';
import { Email } from '../types/email.interface';
import * as fs from 'fs';

/* fonction pour importer les mails en exécutant le script Python list-emails.py */

export function retrieveEmails(): Promise<Email[]> {
  return new Promise((resolve, reject) => {
    const process = exec(
      'python ./src/python/scripts/windows/list_emails.py',
      (error, stdout, stderr) => {
        if (error) {
          reject(error);
        } else {
          try {
            console.log('executing script list_emails');
            const jsonOutput = fs.readFileSync(
              './src/python/output/emails.json',
              'utf-8',
            );
            const emails: Email[] = JSON.parse(jsonOutput);
            resolve(emails);
          } catch (parseError) {
            reject(parseError);
          }
        }
      },
    );
  });
}
