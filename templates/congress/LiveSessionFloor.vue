<template>
  <div>
    <!-- Header bar -->
    <div class="card mb-3">
      <div class="card-header d-flex justify-content-between align-items-center">
        <div>
          <strong>Session Floor Control</strong>
          <span class="badge ml-2"
                :class="sessionActive ? 'badge-success' : 'badge-secondary'">
            {{ sessionActive ? 'Active' : 'Closed' }}
          </span>
        </div>
        <div>
          <button v-if="!wsConnected" class="btn btn-sm btn-outline-secondary" @click="connectWs">
            Connect
          </button>
          <span v-else class="text-success small">● Live</span>
        </div>
      </div>
    </div>

    <div class="row">
      <!-- Left column: Current legislation + speaker -->
      <div class="col-md-8">
        <!-- Current Legislation -->
        <div class="card mb-3">
          <div class="card-header d-flex justify-content-between">
            <strong>Current Legislation</strong>
            <button class="btn btn-outline-primary btn-sm" @click="showChangeLegislation = true">
              Change
            </button>
          </div>
          <div class="card-body" v-if="currentLegislation">
            <h5>{{ currentLegislation.code }} — {{ currentLegislation.title }}</h5>
            <p class="text-muted small mb-1">{{ currentLegislation.type }}</p>
            <p>{{ currentLegislation.synopsis }}</p>
          </div>
          <div class="card-body text-muted" v-else>No legislation selected.</div>
        </div>

        <!-- Change Legislation Modal -->
        <div v-if="showChangeLegislation" class="card mb-3 border-primary">
          <div class="card-header">Select Legislation</div>
          <div class="card-body">
            <select class="form-control mb-2" v-model="newDocketItemId">
              <option :value="null">-- pick --</option>
              <option v-for="d in docketItems" :key="d.id" :value="d.id">
                {{ d.legislation_code }} — {{ d.legislation_title }}
              </option>
            </select>
            <button class="btn btn-primary btn-sm" :disabled="!newDocketItemId" @click="changeLegislation">
              Confirm
            </button>
            <button class="btn btn-secondary btn-sm ml-1" @click="showChangeLegislation = false">Cancel</button>
          </div>
        </div>

        <!-- Current Speaker -->
        <div class="card mb-3">
          <div class="card-header"><strong>Current Speaker</strong></div>
          <div class="card-body" v-if="currentSpeaker">
            <div class="d-flex justify-content-between align-items-center mb-2">
              <div>
                <h5 class="mb-0">{{ currentSpeaker.legislator_name }}</h5>
                <small class="text-muted">{{ currentSpeaker.speech_type }}</small>
              </div>
              <div class="h3 mb-0" :class="timerClass">{{ formattedTime }}</div>
            </div>
            <div class="progress mb-2" style="height: 8px;">
              <div class="progress-bar" :class="timerBarClass"
                   :style="{ width: timerPercent + '%' }" role="progressbar"></div>
            </div>
            <div>
              <button class="btn btn-danger btn-sm" @click="endSpeech">End Speech</button>
              <button class="btn btn-info btn-sm ml-1" @click="openQuestions"
                      v-if="!questionsOpen">Open Questions</button>
              <button class="btn btn-warning btn-sm ml-1" @click="closeQuestions"
                      v-if="questionsOpen">Close Questions</button>
            </div>
          </div>
          <div class="card-body text-muted" v-else>No speaker on the floor.</div>
        </div>

        <!-- Speeches list -->
        <div class="card mb-3">
          <div class="card-header"><strong>Speeches This Legislation</strong></div>
          <ul class="list-group list-group-flush">
            <li v-for="s in speeches" :key="s.id"
                class="list-group-item d-flex justify-content-between align-items-center">
              <div>
                <strong>{{ s.legislator_name }}</strong>
                <span class="badge badge-secondary ml-1">{{ s.speech_type }}</span>
              </div>
              <span class="text-muted small">{{ formatDuration(s.duration_seconds) }}</span>
            </li>
            <li v-if="speeches.length === 0" class="list-group-item text-muted">No speeches yet.</li>
          </ul>
        </div>

        <!-- Voting -->
        <div class="card mb-3">
          <div class="card-header d-flex justify-content-between align-items-center">
            <strong>Vote</strong>
          </div>
          <div class="card-body">
            <button class="btn btn-outline-primary btn-sm mr-2" @click="callVote" :disabled="voteOpen">
              Call Vote
            </button>
            <div v-if="voteOpen" class="mt-2">
              <div class="btn-group">
                <button class="btn btn-success btn-sm" @click="recordVote('PASS')">Pass</button>
                <button class="btn btn-danger btn-sm" @click="recordVote('FAIL')">Fail</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right column: Precedence queue -->
      <div class="col-md-4">
        <div class="card mb-3">
          <div class="card-header d-flex justify-content-between align-items-center">
            <strong>Precedence Queue</strong>
            <button class="btn btn-outline-success btn-sm" @click="autoRecognize" :disabled="!!currentSpeaker">
              Auto‑Select
            </button>
          </div>
          <ul class="list-group list-group-flush">
            <li v-for="(leg, idx) in precedenceQueue" :key="leg.legislator_id"
                class="list-group-item d-flex justify-content-between align-items-center">
              <div>
                <span class="badge badge-pill badge-light mr-1">{{ idx + 1 }}</span>
                {{ leg.display_name }}
                <br>
                <small class="text-muted">
                  Spoke {{ leg.speech_count }}× · Recency {{ leg.recency_rank }}
                </small>
              </div>
              <button class="btn btn-success btn-sm" title="Recognize"
                      :disabled="!!currentSpeaker"
                      @click="recognizeSpeaker(leg.legislator_id, 'AUTHORSHIP')">
                ✓
              </button>
            </li>
            <li v-if="precedenceQueue.length === 0" class="list-group-item text-muted">
              Queue empty.
            </li>
          </ul>
        </div>

        <!-- Questioner queue -->
        <div class="card" v-if="questionsOpen">
          <div class="card-header"><strong>Questioner Queue</strong></div>
          <ul class="list-group list-group-flush">
            <li v-for="q in questionerQueue" :key="q.legislator_id"
                class="list-group-item">
              {{ q.display_name }}
            </li>
            <li v-if="questionerQueue.length === 0" class="list-group-item text-muted">
              No questioners.
            </li>
          </ul>
        </div>
      </div>
    </div>

    <div v-if="error" class="alert alert-danger mt-2">{{ error }}</div>
  </div>
</template>

<script>
export default {
  name: 'CongressLiveSessionFloor',
  data () {
    const cfg = window.congressConfig || {}
    return {
      config: cfg,
      sessionId: cfg.sessionId,
      chamberId: cfg.chamberId,
      sessionActive: false,
      currentLegislation: null,
      currentSpeaker: null,
      speeches: [],
      precedenceQueue: [],
      questionerQueue: [],
      questionsOpen: false,
      voteOpen: false,
      docketItems: [],
      newDocketItemId: null,
      showChangeLegislation: false,
      // Timer
      timerSeconds: 0,
      timerLimit: 180,
      timerInterval: null,
      // WebSocket
      ws: null,
      wsConnected: false,
      error: null,
    }
  },
  computed: {
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
    this.loadDocket()
    if (this.chamberId) this.connectWs()
  },
  beforeDestroy () {
    this.stopTimer()
    if (this.ws) this.ws.close()
  },
  methods: {
    headers () {
      return {
        'Content-Type': 'application/json',
        'X-Congress-Api-Key': this.config.apiKey,
      }
    },
    api (path, opts) {
      return fetch(`${this.config.nekocongressUrl}${path}`, {
        headers: this.headers(),
        ...opts,
      })
    },
    async loadSession () {
      try {
        const resp = await this.api(`/api/congress/sessions/${this.sessionId}/`)
        if (!resp.ok) return
        const data = await resp.json()
        this.sessionActive = data.status === 'ACTIVE'
        this.chamberId = data.chamber_id
        this.currentLegislation = data.current_legislation || null
        await this.loadPrecedenceQueue()
        await this.loadSpeeches()
      } catch (e) {
        this.error = e.message
      }
    },
    async loadDocket () {
      try {
        const resp = await this.api(`/api/congress/docket/session/${this.sessionId}/`)
        if (resp.ok) this.docketItems = await resp.json()
      } catch (_) { /* ignore */ }
    },
    async loadPrecedenceQueue () {
      try {
        const resp = await this.api(`/api/congress/sessions/${this.sessionId}/precedence/`)
        if (resp.ok) this.precedenceQueue = await resp.json()
      } catch (_) { /* ignore */ }
    },
    async loadSpeeches () {
      try {
        const resp = await this.api(
          `/api/congress/floor/speeches/${this.sessionId}/`
        )
        if (resp.ok) this.speeches = await resp.json()
      } catch (_) { /* ignore */ }
    },
    async recognizeSpeaker (legislatorId, speechType) {
      this.error = null
      try {
        const resp = await this.api(`/api/congress/floor/recognize-speaker/`, {
          method: 'POST',
          body: JSON.stringify({
            session_id: this.sessionId,
            legislator_id: legislatorId,
            speech_type: speechType,
          }),
        })
        if (!resp.ok) throw new Error((await resp.json()).detail)
        const data = await resp.json()
        this.currentSpeaker = data
        this.startTimer()
      } catch (e) {
        this.error = e.message
      }
    },
    async autoRecognize () {
      this.error = null
      try {
        const resp = await this.api(`/api/congress/floor/recognize-speaker/`, {
          method: 'POST',
          body: JSON.stringify({ session_id: this.sessionId }),
        })
        if (!resp.ok) throw new Error((await resp.json()).detail)
        const data = await resp.json()
        this.currentSpeaker = data
        this.startTimer()
      } catch (e) {
        this.error = e.message
      }
    },
    async endSpeech () {
      this.error = null
      try {
        const resp = await this.api(`/api/congress/floor/end-speech/`, {
          method: 'POST',
          body: JSON.stringify({ session_id: this.sessionId, speech_id: this.currentSpeaker.id }),
        })
        if (!resp.ok) throw new Error((await resp.json()).detail)
        this.stopTimer()
        this.currentSpeaker = null
        await this.loadSpeeches()
        await this.loadPrecedenceQueue()
      } catch (e) {
        this.error = e.message
      }
    },
    async openQuestions () {
      try {
        const resp = await this.api(`/api/congress/floor/open-questions/`, {
          method: 'POST',
          body: JSON.stringify({ speech_id: this.currentSpeaker.id }),
        })
        if (resp.ok) this.questionsOpen = true
      } catch (_) { /* ignore */ }
    },
    async closeQuestions () {
      try {
        const resp = await this.api(`/api/congress/floor/close-questions/`, {
          method: 'POST',
          body: JSON.stringify({ speech_id: this.currentSpeaker.id }),
        })
        if (resp.ok) {
          this.questionsOpen = false
          this.questionerQueue = []
        }
      } catch (_) { /* ignore */ }
    },
    async changeLegislation () {
      this.error = null
      try {
        const resp = await this.api(`/api/congress/floor/change-legislation/`, {
          method: 'POST',
          body: JSON.stringify({
            session_id: this.sessionId,
            docket_item_id: this.newDocketItemId,
          }),
        })
        if (!resp.ok) throw new Error((await resp.json()).detail)
        this.currentLegislation = await resp.json()
        this.showChangeLegislation = false
        this.speeches = []
        await this.loadPrecedenceQueue()
      } catch (e) {
        this.error = e.message
      }
    },
    async callVote () {
      try {
        const resp = await this.api(`/api/congress/floor/call-vote/`, {
          method: 'POST',
          body: JSON.stringify({
            session_id: this.sessionId,
            docket_item_id: this.currentLegislation ? this.currentLegislation.docket_item_id : 0,
          }),
        })
        if (resp.ok) this.voteOpen = true
      } catch (_) { /* ignore */ }
    },
    async recordVote (result) {
      try {
        await this.api(`/api/congress/floor/record-vote/`, {
          method: 'POST',
          body: JSON.stringify({
            session_id: this.sessionId,
            docket_item_id: this.currentLegislation ? this.currentLegislation.docket_item_id : 0,
            result,
            aff_votes: 0,
            neg_votes: 0,
          }),
        })
        this.voteOpen = false
      } catch (_) { /* ignore */ }
    },
    /* Timer */
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
    formatDuration (secs) {
      if (!secs) return '—'
      const m = Math.floor(secs / 60)
      const s = secs % 60
      return `${m}:${String(s).padStart(2, '0')}`
    },
    /* WebSocket */
    connectWs () {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const base = this.config.nekocongressUrl.replace(/^https?/, proto)
      const url = `${base}/api/congress/ws/chamber/${this.chamberId}/?token=${encodeURIComponent(this.config.token)}`
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
          this.loadSpeeches()
          this.loadPrecedenceQueue()
        },
        LEGISLATION_CHANGED: () => {
          this.currentLegislation = msg.payload
          this.speeches = []
          this.loadPrecedenceQueue()
        },
        QUESTIONS_OPENED: () => { this.questionsOpen = true },
        QUESTIONS_CLOSED: () => { this.questionsOpen = false; this.questionerQueue = [] },
        QUESTIONER_QUEUED: () => {
          this.questionerQueue.push(msg.payload)
        },
        VOTE_CALLED: () => { this.voteOpen = true },
        VOTE_RECORDED: () => { this.voteOpen = false },
        QUEUE_UPDATED: () => { this.loadPrecedenceQueue() },
      }
      const handler = handlers[msg.event_type]
      if (handler) handler()
    },
  },
}
</script>
