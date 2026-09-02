<template>
    <div>
        <div v-if="status">
            <h2>{{ status.data }}</h2>
        </div>
    </div>
</template>

<script>
import io from 'socket.io-client'

export default {
    data() {
        return {
            status: null,
        }
    },
    mounted() {
        const socket = io('http://localhost:5000')

        // status event listener
        socket.on('status', (data) => {
            console.log(data)
            this.status = JSON.parse(data)
        })
    },
}
</script>

<style>
/* Your component styles here */
</style>
