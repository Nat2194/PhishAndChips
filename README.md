## Phish And Chips

### How to install PhishAndChips

1. Clone the repository

   ```bash
   $ git clone [https://github.com/Nat2194/PhishAndChips](https://github.com/Nat2194/PhishAndChips)
   $ cd PhishAndChips
   ```

2. Run these commands in the root of the project to install dependencies:

   ```bash
   $ cd api
   $ npm i
   $ npm run i:python
   $ cd ../website
   $ npm i
   ```

3. Go to [this guide](https://github.com/Nat2194/PhishAndChips/tree/main/docker) and follow all the instructions to set up the Docker container.

### Setting up the Gmail API Service Account

The backend Python API requires a Google Cloud Service Account to interact with Gmail.

1. **Enable the Gmail API**

   - Open the [Google Cloud Console](https://console.cloud.google.com/).
   - Select or create a project.
   - Navigate to **APIs & Services > Library**, search for **Gmail API**, and click **Enable**.

2. **Create the Service Account**

   - Go to **APIs & Services > Credentials**.
   - Click **Create Credentials** and select **Service account**.
   - Enter a name (e.g., `phishandchips-gmail-service`) and complete the creation process.

3. **Generate the Key (JSON)**

   - Select the newly created service account from the list.
   - Go to the **Keys** tab, click **Add Key > Create new key**, choose **JSON**, and click **Create**.
   - Save the downloaded `.json` file inside your backend directory (e.g., inside `api/src/python/`).
   - **Security Notice:** Ensure this `.json` file is added to your `.gitignore` to avoid committing API credentials.

4. **Domain-Wide Delegation (Google Workspace)**
   - _If accessing user mailboxes directly with a service account:_
   - Copy the **Unique ID / Client ID** of your service account from the Google Cloud Console.
   - In the [Google Admin Console](https://admin.google.com/), go to **Security > Access and data control > API controls > Manage Domain-Wide Delegation**.
   - Add a new API client using the Client ID and provide the required OAuth scopes (e.g., `https://mail.google.com/`).

### How to run the application

1. Open a terminal and run the API backend:

   ```bash
   $ cd api
   $ npm run start
   ```

2. Open a new terminal and run the frontend:

   ```bash
   $ cd website
   $ npm run dev
   ```

3. Open your browser and navigate to `http://127.0.0.1:5173/` (or the port displayed by Vite).

You are now ready to start! Send your first email to the address configured in the backend and click on "Obtenir les emails" in the app. Then, select the mail you want to analyze and wait for the results.
