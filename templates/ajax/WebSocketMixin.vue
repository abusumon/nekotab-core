<script>
// Subclass should set following methods
// - Optional computed property of "tournamentSlugForWSPath" with a tournament slug for the path
// - Optional computed property  of "roundSlugForWSPath" with a round sequence ID for the path
// - a data prop of "sockets" that for all the socket paths to monitor
// - a handleSocketReceive() function that will handle the different
// sockets' messages as appropriate

import { WebSocketBridge } from 'django-channels'
import ModalErrorMixin from '../errors/ModalErrorMixin.vue'

export default {
  mixins: [ModalErrorMixin],
  data: function () {
    return {
      bridges: {},
      lostConnections: 0,
      componentId: Math.floor(Math.random() * 10000),
      lostConnectionTimer: null,
    }
  },
  created: function () {
    // Check if this is being run over HTTP(S); match the WS(S) protocol
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const path = `${scheme}://${window.location.host}/ws/`
    // Construct path

    const receiveFromSocket = this.receiveFromSocket
    const self = this

    // Setup each websocket connection
    for (const socketLabel of this.sockets) {
      // Customise path per-socket
      const socketPath = self.getPathAdditions(path, socketLabel)

      // Open the connection
      const webSocketBridge = new WebSocketBridge()
      // Reconnect fast and keep retrying often.
      //
      // The old settings waited 5s before the first retry and backed off to a
      // 4-minute ceiling. During a live round that is the difference between a
      // blip nobody notices and a tab table sitting in front of a "Connection
      // Lost" banner, unable to trust the screen, for minutes at a time. A
      // deploy or a worker restart is over in seconds, so retrying quickly
      // costs one or two extra attempts and recovers almost immediately.
      webSocketBridge.connect(socketPath, undefined, {
        minReconnectionDelay: 1 * 1000, // First retry after ~1s
        maxReconnectionDelay: 20 * 1000, // Never wait more than 20s to retry
        reconnectionDelayGrowFactor: 1.3,
        connectionTimeout: 10 * 1000,
      })

      // Listen for messages and pass to the defined handleSocketMessage()
      webSocketBridge.addEventListener('message', (payload) => {
        receiveFromSocket(socketLabel, payload.data)
      })

      // Logs
      webSocketBridge.socket.addEventListener('open', (() => {
        self.logConnectionInfo('connected to', socketPath)
        self.dismissLostConnectionAlert()
      }).bind(socketPath, self))
      webSocketBridge.socket.addEventListener('error', (() => {
        self.logConnectionInfo('error in', socketPath)
      }).bind(socketPath, self))
      webSocketBridge.socket.addEventListener('close', (() => {
        self.lostConnections += 1
        self.logConnectionInfo('disconnected from', socketPath)
        self.showLostConnectionAlert()
      }).bind(socketPath, self))

      // Set the data to contain the socket bridge so that we can send to it
      self.$set(self.bridges, socketLabel, webSocketBridge)
    }
  },
  methods: {
    getPathAdditions: function (path, socketLabel) {
      // Allows for manual overrides to provide full paths
      if (this.tournamentSlugForWSPath !== undefined) {
        path += `${this.tournamentSlugForWSPath}/`
      }
      if (this.roundSlugForWSPath !== undefined) {
        path += `round/${this.roundSlugForWSPath}/`
      }
      path = `${path + socketLabel}/`
      return path
    },
    logConnectionInfo: function (statusType, socketPath) {
      const now = new Date()
      const paddedMinutes = now.getMinutes() < 10 ? '0' + now.getMinutes() : now.getMinutes()
      const msg = `${now.getHours()}:${paddedMinutes} ${statusType} path:\n${socketPath}`
      console.debug(`${msg}\n(${this.lostConnections} prior loses)`)
    },
    // Passes to inheriting components; receives a payload from a socket
    receiveFromSocket: function (socketLabel, payload) {
      // console.log(`Received payload ${JSON.stringify(payload)} from socket ${socketLabel}`)
      if (Object.prototype.hasOwnProperty.call(payload, 'error')) {
        if (payload.component_id === this.componentId) {
          this.showErrorAlert(payload.error, payload.message, null)
        }
      } else {
        this.handleSocketReceive(socketLabel, payload)
      }
    },
    // Called by inheriting components; sends a given payload to a socket
    sendToSocket: function (socketLabel, payload) {
      // console.log(`Sent payload ${JSON.stringify(payload)} to socket ${socketLabel}`)
      payload.component_id = this.componentId // Pass on originating Vue instance
      this.bridges[socketLabel].send(payload)
    },
    // Warn only if the connection is still down after a grace period.
    //
    // Reconnection now takes about a second, so alerting the instant a socket
    // closes means flashing an alarming red modal for a hiccup that has already
    // fixed itself. That is what made the banner feel constant: most sightings
    // were of a connection that was fine again before the user finished
    // reading. Waiting a few seconds means the warning appears only when
    // something is genuinely wrong — which is the only time it is useful.
    showLostConnectionAlert: function () {
      if (this.lostConnections <= 1) {
        return
      }
      if (this.lostConnectionTimer !== null) {
        return // Already counting down from an earlier close
      }
      this.lostConnectionTimer = window.setTimeout(() => {
        this.lostConnectionTimer = null
        const explanation = `This page maintains a live connection to the server. That connection has
                           been lost. This page will attempt to reconnect and will update this message
                           if it succeeds. You can dismiss this warning if needed, just be aware that
                           you should not change data on this page until the connection resumes.`
        this.showErrorAlert(explanation, null, 'Connection Lost', 'text-danger', true, true)
      }, 5000)
    },
    dismissLostConnectionAlert: function () {
      // Reconnected inside the grace period: cancel the pending warning and
      // say nothing at all. The user never knew, and telling them now would
      // only invent a problem.
      if (this.lostConnectionTimer !== null) {
        window.clearTimeout(this.lostConnectionTimer)
        this.lostConnectionTimer = null
        return
      }
      if (this.lostConnections > 1) { // Only show modal when a connection is re-opened not opened
        const explanation = `This page lost its connection to the server but has successfully reopened
                           it. Changes made to data on this page will now be saved. However, you may
                           want to refresh the page to verify that earlier changes were saved.`
        this.showErrorAlert(explanation, null, 'Connection Resumed', 'text-success', true, true)
      }
    },
  },
}
</script>
