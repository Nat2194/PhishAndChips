import { exec } from 'child_process';
import * as fs from 'fs';

export function analyseMail(mailUid: string, port: number): Promise<string> {
  return new Promise((resolve, reject) => {
    exec(
      `python ./src/python/scripts/windows/analyse.py ${mailUid} ${port}`,
      (error, stdout, stderr) => {
        if (error) {
          reject(error);
        } else {
          console.log(stdout);
          const response: string = stdout;
          resolve(response);
        }
      },
    );
  });
}
