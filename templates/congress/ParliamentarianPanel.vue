<template>
  <div>
    <div class="card mb-3">
      <div class="card-header"><strong>Parliamentarian Panel</strong></div>
    </div>

    <!-- Parliamentarian Rankings -->
    <div class="card mb-3">
      <div class="card-header"><strong>Parliamentarian Rankings</strong></div>
      <div class="card-body">
        <p class="text-muted small">
          Rank legislators on parliamentary procedure and debate quality.
        </p>
        <table class="table table-sm">
          <thead>
            <tr>
              <th style="width:80px">Rank</th>
              <th>Legislator</th>
              <th>Speeches</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="leg in rankedLegislators" :key="leg.legislator_id">
              <td>
                <input type="number" class="form-control form-control-sm"
                       v-model.number="leg.rank_position" min="1" :max="rankedLegislators.length" />
              </td>
              <td>{{ leg.display_name }}</td>
              <td>{{ leg.speech_count }}</td>
            </tr>
          </tbody>
        </table>
        <button class="btn btn-success btn-sm" :disabled="submittingRankings"
                @click="submitRankings">
          {{ submittingRankings ? 'Saving…' : 'Submit Rankings' }}
        </button>
      </div>
    </div>

    <!-- Amendment Review -->
    <div class="card mb-3">
      <div class="card-header d-flex justify-content-between align-items-center">
        <strong>Amendments Pending Review</strong>
        <button class="btn btn-outline-secondary btn-sm" @click="loadAmendments">Refresh</button>
      </div>
      <div class="card-body p-0">
        <table class="table table-sm mb-0" v-if="amendments.length">
          <thead>
            <tr>
              <th>Proposed By</th>
              <th>Type</th>
              <th>Text</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="a in amendments" :key="a.id"
                :class="{
                  'table-success': a.status === 'APPROVED',
                  'table-danger': a.status === 'REJECTED'
                }">
              <td>{{ a.proposer_name }}</td>
              <td><span class="badge badge-secondary">{{ a.amendment_type }}</span></td>
              <td>{{ a.text }}</td>
              <td>
                <div v-if="a.status === 'PENDING'" class="btn-group btn-group-sm">
                  <button class="btn btn-success" @click="reviewAmendment(a.id, true)">
                    Germane
                  </button>
                  <button class="btn btn-danger" @click="reviewAmendment(a.id, false)">
                    Not Germane
                  </button>
                </div>
                <span v-else class="badge"
                      :class="a.status === 'APPROVED' ? 'badge-success' : 'badge-danger'">
                  {{ a.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="p-3 text-muted">No amendments to review.</div>
      </div>
    </div>

    <!-- PO Evaluation -->
    <div class="card mb-3" v-if="poLegislatorId">
      <div class="card-header"><strong>PO Evaluation</strong></div>
      <div class="card-body">
        <div class="form-group">
          <label>PO Points ({{ config.scoreMin || 1 }}–{{ config.scoreMax || 8 }})</label>
          <input type="number" class="form-control" v-model.number="poScore"
                 :min="config.scoreMin || 1" :max="config.scoreMax || 8" />
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
  name: 'CongressParliamentarianPanel',
  data () {
    const cfg = window.congressConfig || {}
    return {
      config: cfg,
      sessionId: cfg.sessionId,
      poLegislatorId: cfg.poLegislatorId || null,
      rankedLegislators: [],
      amendments: [],
      poScore: null,
      submittingRankings: false,
      submittingPo: false,
      successMsg: null,
      error: null,
    }
  },
  mounted () {
    this.loadLegislators()
    this.loadAmendments()
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
    flashSuccess (msg) {
      this.successMsg = msg
      setTimeout(() => { this.successMsg = null }, 3000)
    },
    async loadLegislators () {
      try {
        // Get speeches to build legislator list with counts
        const resp = await this.api(`/api/congress/floor/speeches/${this.sessionId}/`)
        if (!resp.ok) return
        const speeches = await resp.json()
        const byLeg = {}
        for (const s of speeches) {
          if (!byLeg[s.legislator_id]) {
            byLeg[s.legislator_id] = {
              legislator_id: s.legislator_id,
              display_name: s.legislator_name,
              speech_count: 0,
              rank_position: null,
            }
          }
          byLeg[s.legislator_id].speech_count++
        }
        this.rankedLegislators = Object.values(byLeg)
          .sort((a, b) => b.speech_count - a.speech_count)
          .map((l, i) => ({ ...l, rank_position: i + 1 }))
      } catch (_) { /* ignore */ }
    },
    async loadAmendments () {
      try {
        // Load amendments for current docket item if available
        if (!this.config.currentDocketItemId) return
        const resp = await this.api(
          `/api/congress/amendments/docket-item/${this.config.currentDocketItemId}/`
        )
        if (resp.ok) this.amendments = await resp.json()
      } catch (_) { /* ignore */ }
    },
    async submitRankings () {
      this.submittingRankings = true
      this.error = null
      try {
        const rankings = this.rankedLegislators.map(l => ({
          legislator_id: l.legislator_id,
          rank_position: l.rank_position,
        }))
        const resp = await this.api(`/api/congress/scores/rankings/parliamentarian/`, {
          method: 'POST',
          body: JSON.stringify({
            session_id: this.sessionId,
            scorer_id: this.config.judgerId,
            rankings,
          }),
        })
        if (!resp.ok) throw new Error((await resp.json()).detail)
        this.flashSuccess('Parliamentarian rankings submitted.')
      } catch (e) {
        this.error = e.message
      } finally {
        this.submittingRankings = false
      }
    },
    async reviewAmendment (amendmentId, isGermane) {
      this.error = null
      try {
        const resp = await this.api(`/api/congress/amendments/${amendmentId}/review/`, {
          method: 'POST',
          body: JSON.stringify({ is_germane: isGermane }),
        })
        if (!resp.ok) throw new Error((await resp.json()).detail)
        await this.loadAmendments()
      } catch (e) {
        this.error = e.message
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
  },
}
</script>
