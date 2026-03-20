<template>
  <div>
    <div class="card mb-3">
      <div class="card-header"><strong>Scorer Ballot</strong></div>
    </div>

    <!-- Current speaker info (read-only from WS) -->
    <div class="card mb-3" v-if="currentSpeaker">
      <div class="card-body">
        <h5>{{ currentSpeaker.legislator_name }}</h5>
        <span class="badge badge-info">{{ currentSpeaker.speech_type }}</span>
      </div>
    </div>

    <!-- Speech Scoring -->
    <div class="card mb-3">
      <div class="card-header"><strong>Score Speech</strong></div>
      <div class="card-body">
        <div class="form-group">
          <label>Legislator</label>
          <select class="form-control" v-model="scoreForm.speech_id">
            <option :value="null">-- select speech --</option>
            <option v-for="s in speeches" :key="s.id" :value="s.id">
              {{ s.legislator_name }} — {{ s.speech_type }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>Points ({{ scoreMin }}–{{ scoreMax }})</label>
          <input type="number" class="form-control" v-model.number="scoreForm.points"
                 :min="scoreMin" :max="scoreMax" />
        </div>
        <button class="btn btn-primary btn-sm" :disabled="!scoreForm.speech_id || submittingScore"
                @click="submitScore">
          {{ submittingScore ? 'Saving…' : 'Submit Score' }}
        </button>
      </div>
    </div>

    <!-- Session Rankings -->
    <div class="card mb-3">
      <div class="card-header"><strong>Session Rankings</strong></div>
      <div class="card-body">
        <p class="text-muted small">Drag or enter rank numbers. Lower rank = better.</p>
        <table class="table table-sm">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Legislator</th>
              <th>Total Pts</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(leg, idx) in rankedLegislators" :key="leg.legislator_id">
              <td style="width:80px">
                <input type="number" class="form-control form-control-sm"
                       v-model.number="leg.rank_position" min="1" :max="rankedLegislators.length" />
              </td>
              <td>{{ leg.display_name }}</td>
              <td>{{ leg.total_points }}</td>
            </tr>
          </tbody>
        </table>
        <button class="btn btn-success btn-sm" :disabled="submittingRankings"
                @click="submitRankings">
          {{ submittingRankings ? 'Saving…' : 'Submit Rankings' }}
        </button>
      </div>
    </div>

    <!-- PO Score -->
    <div class="card mb-3" v-if="poLegislatorId">
      <div class="card-header"><strong>PO Score</strong></div>
      <div class="card-body">
        <div class="form-group">
          <label>PO Points ({{ scoreMin }}–{{ scoreMax }})</label>
          <input type="number" class="form-control" v-model.number="poScore"
                 :min="scoreMin" :max="scoreMax" />
        </div>
        <button class="btn btn-primary btn-sm" :disabled="submittingPo" @click="submitPoScore">
          {{ submittingPo ? 'Saving…' : 'Submit PO Score' }}
        </button>
      </div>
    </div>

    <div v-if="successMsg" class="alert alert-success">{{ successMsg }}</div>
    <div v-if="error" class="alert alert-danger">{{ error }}</div>
  </div>
</template>

<script>
export default {
  name: 'CongressScorerBallot',
  data () {
    const cfg = window.congressConfig || {}
    return {
      config: cfg,
      sessionId: cfg.sessionId,
      chamberId: cfg.chamberId,
      scoreMin: cfg.scoreMin || 1,
      scoreMax: cfg.scoreMax || 8,
      currentSpeaker: null,
      speeches: [],
      rankedLegislators: [],
      poLegislatorId: cfg.poLegislatorId || null,
      scoreForm: { speech_id: null, points: null },
      poScore: null,
      submittingScore: false,
      submittingRankings: false,
      submittingPo: false,
      successMsg: null,
      error: null,
      ws: null,
    }
  },
  async mounted () {
    await this.loadSession()
    await this.loadSpeeches()
    this.loadScores()
    if (this.chamberId) this.connectWs()
  },
  beforeDestroy () {
    if (this.ws) this.ws.close()
  },
  methods: {
    headers () {
      return {
        'Content-Type': 'application/json',
        'X-Congress-Api-Key': this.config.apiKey,
        Authorization: `Bearer ${this.config.token}`,
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
        if (resp.ok) {
          const data = await resp.json()
          this.chamberId = data.chamber_id
        }
      } catch (_) { /* ignore */ }
    },
    async loadSpeeches () {
      try {
        const resp = await this.api(`/api/congress/floor/speeches/${this.sessionId}/`)
        if (resp.ok) this.speeches = await resp.json()
      } catch (_) { /* ignore */ }
    },
    async loadScores () {
      try {
        const resp = await this.api(`/api/congress/scores/session/${this.sessionId}/`)
        if (resp.ok) {
          const data = await resp.json()
          // Build ranked legislators by cross-referencing speech scores with speeches
          const speechMap = {}
          for (const s of this.speeches) {
            speechMap[s.id] = s
          }
          const byLeg = {}
          for (const sc of data.speech_scores) {
            const speech = speechMap[sc.speech_id]
            if (!speech) continue
            const lid = speech.legislator_id
            if (!byLeg[lid]) {
              byLeg[lid] = {
                legislator_id: lid,
                display_name: speech.legislator_name || '',
                total_points: 0,
                rank_position: null,
              }
            }
            byLeg[lid].total_points += sc.points
          }
          this.rankedLegislators = Object.values(byLeg).sort(
            (a, b) => b.total_points - a.total_points
          ).map((l, i) => ({ ...l, rank_position: i + 1 }))
        }
      } catch (_) { /* ignore */ }
    },
    flashSuccess (msg) {
      this.successMsg = msg
      setTimeout(() => { this.successMsg = null }, 3000)
    },
    async submitScore () {
      this.submittingScore = true
      this.error = null
      try {
        const resp = await this.api(`/api/congress/scores/speech/`, {
          method: 'POST',
          body: JSON.stringify({
            speech_id: this.scoreForm.speech_id,
            scorer_id: this.config.judgerId,
            points: this.scoreForm.points,
          }),
        })
        if (!resp.ok) throw new Error((await resp.json()).detail)
        this.flashSuccess('Score submitted.')
        this.scoreForm = { speech_id: null, points: null }
        await this.loadScores()
      } catch (e) {
        this.error = e.message
      } finally {
        this.submittingScore = false
      }
    },
    async submitRankings () {
      this.submittingRankings = true
      this.error = null
      try {
        const rankings = this.rankedLegislators.map(l => ({
          legislator_id: l.legislator_id,
          rank_position: l.rank_position,
        }))
        const resp = await this.api(`/api/congress/scores/rankings/`, {
          method: 'POST',
          body: JSON.stringify({
            session_id: this.sessionId,
            scorer_id: this.config.judgerId,
            rankings,
          }),
        })
        if (!resp.ok) throw new Error((await resp.json()).detail)
        this.flashSuccess('Rankings submitted.')
      } catch (e) {
        this.error = e.message
      } finally {
        this.submittingRankings = false
      }
    },
    async submitPoScore () {
      this.submittingPo = true
      this.error = null
      try {
        const resp = await this.api(`/api/congress/scores/po/`, {
          method: 'POST',
          body: JSON.stringify({
            session_id: this.sessionId,
            scorer_id: this.config.judgerId,
            hour_number: 1,
            points: this.poScore,
          }),
        })
        if (!resp.ok) throw new Error((await resp.json()).detail)
        this.flashSuccess('PO score submitted.')
      } catch (e) {
        this.error = e.message
      } finally {
        this.submittingPo = false
      }
    },
    /* WebSocket — scorer role for live updates */
    connectWs () {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const base = this.config.nekocongressUrl.replace(/^https?/, proto)
      const url = `${base}/api/congress/ws/scorer/${this.chamberId}/?token=${encodeURIComponent(this.config.token)}`
      this.ws = new WebSocket(url)
      this.ws.onclose = () => { setTimeout(() => this.connectWs(), 3000) }
      this.ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data)
          if (msg.event_type === 'SPEAKER_RECOGNIZED') {
            this.currentSpeaker = msg.payload
          } else if (msg.event_type === 'SPEECH_ENDED') {
            this.currentSpeaker = null
            this.loadSpeeches()
          }
        } catch (_) { /* ignore */ }
      }
    },
  },
}
</script>
