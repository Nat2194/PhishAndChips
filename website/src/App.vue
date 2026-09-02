<template>
    <div id="app">
        <img class="logo" alt="Phish And Chips logo" src="./assets/logo.svg" />
        <ControlPanel />
        <TestFusion />
    </div>
</template>

<script>
import TestFusion from './components/TestFusion.vue'
import ControlPanel from './components/ControlPanel.vue'

export default {
    name: 'App',
    components: {
        ControlPanel,
        TestFusion,
    },
}
</script>

<style>
#app {
    font-family: Avenir, Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-align: center;
    color: #2c3e50;
    margin-top: 60px;
}

.logo {
    max-width: 50%;
}
</style>
