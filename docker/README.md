### Run the containers with Docker Compose

1. Clone the repository

   ```bash
   $ git clone <Your-Repository-URL>
   ```

2. Initialize the secrets and SSL certificates. This script generates unique keys for TheHive/Cortex and local TLS certificates for MISP.

   ```bash
   $cd PhishAndChips/docker$ python init_secrets.py
   ```

3. Run the multi-container application.

   ```bash
   $ docker-compose up -d
   ```

4. If the logs show permission errors regarding the `vol` folder, you need to change the ownership to match the user running the containers.
   ```bash
   $docker-compose stop$ sudo chown -R 1000:1000 vol/index vol/data vol/elastic*
   $ docker-compose up -d
   ```
