<template>
    <div class="email-app">
        <div class="email-list-container">
            <h1 class="title">Emails</h1>
            <button class="button" @click="getEmails">
                Obtenir les emails
            </button>
            <ul v-if="emails.length > 0" class="email-list">
                <li
                    v-for="email in emails"
                    :key="email.mailUID"
                    class="email-item"
                >
                    <button
                        class="email-button"
                        @click="createSocketServer(email.mailUID, 5001)"
                    >
                        <div class="email-header">
                            <div class="email-from">
                                {{ extractEmailSender(email.from) }}
                            </div>
                            <div class="email-date">
                                {{ formatDate(email.date) }}
                            </div>
                        </div>
                        <h2 class="email-subject">{{ email.subject }}</h2>
                        <div class="email-body">{{ email.body }}</div>
                    </button>
                    <ul v-if="socketData[email.mailUID]" class="socket-list">
                        <li
                            v-for="socketMessage in socketData[email.mailUID]"
                            :key="socketMessage"
                            class="socket-item"
                        >
                            {{ socketMessage }}
                        </li>
                    </ul>
                </li>
            </ul>
            <p v-else class="no-email">Aucun email disponible</p>
        </div>
    </div>
</template>
<script>
import axios from 'axios'
import io from 'socket.io-client'

export default {
    components: {},
    data() {
        return {
            emails: [],
            verdict: null,
            socket: null,
            socketData: {}, // Dictionnaire pour stocker les données des sockets
        }
    },
    beforeUnmount() {
        this.disconnectSocket()
    },
    methods: {
        async getEmails() {
            try {
                const response = await axios.get('/mail')
                this.emails = response.data
            } catch (error) {
                console.error(error)
            }
        },
        extractEmailSender(from) {
            const senderMatch = from.match(/([^<]+)<([^>]+)>/)
            if (senderMatch && senderMatch.length === 3) {
                return senderMatch[1].trim()
            }
            return from
        },
        formatDate(timestamp) {
            const date = new Date(parseInt(timestamp))
            return date.toLocaleString('fr-FR', {
                dateStyle: 'short',
                timeStyle: 'short',
            })
        },
        async createSocketServer(mailUid) {
            try {
                const response = await axios.post(
                    'http://localhost:3000/analysis/socket',
                    {
                        mailUid: mailUid,
                    }
                )

                console.log('here')

                console.log(response.data.port)

                const socketUrl = `http://localhost:${response.data.port}`
                this.socket = io(socketUrl)

                // Écouter les événements socket pour afficher les messages
                this.socket.on('status', (status) => {
                    console.log('Received status:', status)
                    // Ajouter le message au dictionnaire socketData
                    this.socketData[mailUid] = []
                    this.socketData[mailUid].push(status)
                })

                // Appeler l'endpoint d'analyse après avoir initialisé le serveur socket
                await this.analyseEmail(mailUid, response.data.port)
            } catch (error) {
                console.error(error)
            }
        },
        async analyseEmail(mailUid, port) {
            try {
                const response = await axios.post(
                    'http://localhost:3000/analysis/run',
                    {
                        mailUid: mailUid,
                        port: port,
                    }
                )
                this.verdict = response.data
            } catch (error) {
                console.error(error)
            }
        },
        disconnectSocket() {
            if (this.socket) {
                this.socket.disconnect()
                this.socket = null
            }
        },
    },
}
</script>
<style scoped>
.email-app {
    display: flex;
}

.control-panel {
    width: 250px;
    background-color: #f7f7f7;
    padding: 20px;
}

.control-panel-limited-width {
    max-width: 250px;
}

.email-list-container {
    flex: 1;
    padding: 20px;
}

.title {
    font-size: 24px;
    margin-bottom: 10px;
}

.button {
    background-color: #007bff;
    color: #fff;
    border: none;
    padding: 10px 20px;
    border-radius: 4px;
    cursor: pointer;
}

.email-list {
    list-style-type: none;
    padding: 0;
}

.email-item {
    margin-bottom: 20px;
}

.email-button {
    width: 100%;
    padding: 0;
    background: none;
    border: none;
    text-align: left;
    cursor: pointer;
}

.email-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 5px;
    color: #888;
}

.email-from {
    font-weight: bold;
}

.email-subject {
    font-size: 18px;
    margin-bottom: 5px;
}

.email-body {
    white-space: pre-wrap;
    margin-bottom: 5px;
}

.no-email {
    color: #888;
    font-style: italic;
}

.socket-list {
    list-style-type: none;
    padding: 0;
    margin-top: 10px;
}

.socket-item {
    margin-bottom: 5px;
}
</style>
