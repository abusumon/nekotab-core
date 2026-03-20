<template>
  <div>
    <!-- Connection status -->
    <div class="card mb-3">
      <div class="card-header d-flex justify-content-between align-items-center">
        <strong>Session View</strong>
        <span :class="wsConnected ? 'text-success' : 'text-muted'" class="small">
          {{ wsConnected ? '● Live' : '○ Connecting…' }}
        </span>
      </div>
    </div>

    <!-- Current Legislation -->
    <div class="card mb-3">
      <div class="card-header"><strong>Current Legislation</strong></div>
      <div class="card-body" v-if="currentLegislation">
        <h5>{{ currentLegislation.code }} — {{ currentLegislation.title }}</h5>
        <span class="badge badge-info mb-2">{{ currentLegislation.type }}</span>
        <p>{{ currentLegislation.synopsis }}</p>
      </div>
      <div class="card-body text-muted" v-else>Waiting for legislation…</div>
    </div>

    <!-- Current Speaker + Timer -->
    <div class="card mb-3" v-if="currentSpeaker">
      <div class="card-body text-center">
        <h4>{{ currentSpeaker.legislator_name }}</h4>
        <span class="badge badge-secondary mb-2">{{ currentSpeaker.speech_type }}</span>
        <div class="display-3 my-3" :class="timerClass">{{ formattedTime }}</div>
        <div class="progress" style="height: 10px;">
          <div class="progress-bar" :class="timerBarClass"
               :style="{ width: timerPercent + '%' }" role="progressbar"></div>
        </div>
      </div>
    </div>

    <!-- Queue Position -->
    <div class="card mb-3">
      <div class="card-header"><strong>Precedence Queue</strong></div>
      <div class="card-body" v-if="myPosition">
        <p>Your queue position: <strong class="h4">{{ myPosition }}</strong></p>
      </div>
      <div class="card-body text-muted" v-else>
        You are not currently in the queue.
      </div>
      <ul class="list-group list-group-flush">
        <li v-for="(leg, idx) in precedenceQueue" :key="leg.legislator_id"
            class="list-group-item d-flex justify-content-between"
            :class="{ 'list-group-item-primary': leg.legislator_id === config.legislatorId }">
          <span>{{ idx + 1 }}. {{ leg.display_name }}</span>
          <small class="text-muted">{{ leg.speech_count }} speeches</small>
        </li>
      </ul>
    </div>

    <!-- Speech History -->
    <div class="card mb-3">
      <div class="card-header"><strong>Speeches</strong></div>
      <ul class="list-group list-group-flush">
        <li v-for="s in speeches" :key="s.id"
            class="list-group-item d-flex justify-content-between">
          <div>
            <strong>{{ s.legislator_name }}</strong>
            <span class="badge badge-secondary ml-1">{{ s.speech_type }}</span>
          </div>
          <span class="text-muted small">{{ formatDuration(s.duration_seconds) }}</span>
        </li>
        <li v-if="speeches.length === 0" class="list-group-item text-muted">No speeches yet.</li>
      </ul>
    </div>

    <!-- Questions status -->
    <div class="card mb-3" v-if="questionsOpen">
      <div class="card-header"><strong>Questions Open</strong></div>
      <div class="card-body">
        <p>Questions are open for the current speaker.</p>
      </div>
    </div>

    <!-- Vote status -->
    <div class="card" v-if="voteActive">
      <div class="card-header"><strong>Vote in Progress</strong></div>
      <div class="card-body text-center">
        <p class="h5">A vote has been called on the current legislation.</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CongressStudentSessionView',
  data () {
    const cfg = window.congressConfig || {}
    return {
      config: cfg,
      sessionId: cfg.sessionId,
      chamberId: cfg.chamberId,
      currentLegislation: null,
      currentSpeaker: null,
      precedenceQueue: [],
      speeches: [],
      questionsOpen: false,
      voteActive: false,
      timerSeconds: 0,
      timerLimit: 180,
      timerInterval: null,
      ws: null,
      wsConnected: false,
    }
  },
  computed: {
    myPosition () {
      if (!this.config.legislatorId) return null
      const idx = this.precedenceQueue.findIndex(
        l => l.legislator_id === this.config.legislatorId
      )
      return idx >= 0 ? idx + 1 : null
    },
    formattedTime () {
      const m = Math.floor(this.timerSeconds / 60)
      const s = this.timerSeconds % 60
      return `${m}:${String(s).padStart(2, '0')}`
    },
    timerPercent () {
      if (!this.timerLimit) return 0
      return Math.min(100, (this.timerSeconds / this.timerLimit) * 100)
    },
    timerClass () {
      if (this.timerSeconds > this.timerLimit) return 'text-danger'
      if (this.timerSeconds > this.timerLimit * 0.8) return 'text-warning'
      return 'text-dark'
    },
    timerBarClass () {
      if (this.timerSeconds > this.timerLimit) return 'bg-danger'
      if (this.timerSeconds > this.timerLimit * 0.8) return 'bg-warning'
      return 'bg-success'
    },
  },
  async mounted () {
    await this.loadSession()
    this.loadInitialData()
    if (this.chamberId) this.connectWs()
  },
  beforeDestroy () {
    this.stopTimer()
    if (this.ws) this.ws.close()
  },
  methods: {
    headers () {
      return { 'X-Congress-Api-Key': this.config.apiKey }
    },
    api (path) {
      return fetch(`${this.config.nekocongressUrl}${path}`, { headers: this.headers() })
    },
    async loadSession () {
      try {
        const resp = await this.api(`/api/congress/sessions/${this.sessionId}/`)
        if (resp.ok) {
          const data = await resp.json()
          this.chamberId = data.chamber_id
        }
      } catch (_) { /* ignore */ }
    },
    async loadInitialData () {
      try {
        const [speechResp, queueResp] = await Promise.all([
          this.api(`/api/congress/floor/speeches/${this.sessionId}/`),
          this.api(`/api/congress/sessions/${this.sessionId}/precedence/`),
        ])
        if (speechResp.ok) this.speeches = await speechResp.json()
        if (queueResp.ok) this.precedenceQueue = await queueResp.json()
      } catch (_) { /* ignore */ }
    },
    formatDuration (secs) {
      if (!secs) return '—'
      const m = Math.floor(secs / 60)
      const s = secs % 60
      return `${m}:${String(s).padStart(2, '0')}`
    },
    startTimer () {
      this.timerSeconds = 0
      this.stopTimer()
      this.timerInterval = setInterval(() => { this.timerSeconds++ }, 1000)
    },
    stopTimer () {
      if (this.timerInterval) {
        clearInterval(this.timerInterval)
        this.timerInterval = null
      }
    },
    connectWs () {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const base = this.config.nekocongressUrl.replace(/^https?/, proto)
      const url = `${base}/api/congress/ws/student/${this.chamberId}/?token=${encodeURIComponent(this.config.token)}`
      this.ws = new WebSocket(url)
      this.ws.onopen = () => { this.wsConnected = true }
      this.ws.onclose = () => {
        this.wsConnected = false
        setTimeout(() => this.connectWs(), 3000)
      }
      this.ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data)
          this.handleEvent(msg)
        } catch (_) { /* ignore */ }
      }
    },
    handleEvent (msg) {
      const handlers = {
        SPEAKER_RECOGNIZED: () => {
          this.currentSpeaker = msg.payload
          this.startTimer()
        },
        SPEECH_ENDED: () => {
          this.currentSpeaker = null
          this.stopTimer()
          this.loadInitialData()
        },
        LEGISLATION_CHANGED: () => {
          this.currentLegislation = msg.payload
          this.speeches = []
        },
        QUESTIONS_OPENED: () => { this.questionsOpen = true },
        QUESTIONS_CLOSED: () => { this.questionsOpen = false },
        VOTE_CALLED: () => { this.voteActive = true },
        VOTE_RECORDED: () => { this.voteActive = false },
        QUEUE_UPDATED: () => { this.loadInitialData() },
      }
      const handler = handlers[msg.event_type]
      if (handler) handler()
    },
  },
}
</script>
