<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <strong>PO Election — Round {{ currentRound }}</strong>
      <span v-if="electionStatus" class="badge"
            :class="electionStatus === 'DECIDED' ? 'badge-success' : 'badge-info'">
        {{ electionStatus }}
      </span>
    </div>
    <div class="card-body">
      <!-- Not started -->
      <div v-if="!electionStarted">
        <p class="text-muted">Start a Presiding Officer election for this session.</p>
        <button class="btn btn-primary btn-sm" :disabled="starting" @click="startElection">
          {{ starting ? 'Starting…' : 'Start PO Election' }}
        </button>
      </div>

      <!-- Voting phase -->
      <div v-else-if="electionStatus === 'OPEN'">
        <p>Select a candidate and cast your vote:</p>
        <div class="list-group mb-3">
          <button v-for="c in candidates" :key="c.legislator_id"
                  class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
                  :class="{ active: selectedCandidate === c.legislator_id }"
                  @click="selectedCandidate = c.legislator_id">
            {{ c.display_name }}
            <span v-if="c.eliminated" class="badge badge-danger">Eliminated</span>
          </button>
        </div>
        <div class="d-flex justify-content-between">
          <button class="btn btn-success btn-sm"
                  :disabled="!selectedCandidate || voting"
                  @click="castVote">
            {{ voting ? 'Casting…' : 'Cast Vote' }}
          </button>
          <button class="btn btn-outline-primary btn-sm" :disabled="tallying" @click="tallyVotes">
            {{ tallying ? 'Tallying…' : 'Tally Votes' }}
          </button>
        </div>
      </div>

      <!-- Results -->
      <div v-else-if="tallyResult">
        <h6>Round {{ tallyResult.round_number }} Results</h6>
        <table class="table table-sm table-bordered">
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Votes</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in tallyResult.candidates" :key="c.legislator_id"
                :class="{ 'table-success': tallyResult.winner_id === c.legislator_id }">
              <td>{{ c.display_name }}</td>
              <td>{{ c.votes }}</td>
              <td>
                <span v-if="tallyResult.winner_id === c.legislator_id" class="badge badge-success">Winner</span>
                <span v-else-if="c.eliminated" class="badge badge-danger">Eliminated</span>
              </td>
            </tr>
          </tbody>
        </table>
        <p class="text-muted">
          Total: {{ tallyResult.total_votes }} votes · Majority: {{ tallyResult.majority_needed }}
        </p>
        <div v-if="tallyResult.winner_id">
          <div class="alert alert-success">
            <strong>{{ tallyResult.winner_name }}</strong> elected as Presiding Officer!
          </div>
        </div>
        <div v-else>
          <p class="text-warning">No majority reached. Start another round.</p>
          <button class="btn btn-primary btn-sm" @click="startElection">
            Start Round {{ currentRound + 1 }}
          </button>
        </div>
      </div>

      <div v-if="error" class="alert alert-danger mt-2">{{ error }}</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CongressPOElection',
  props: {
    sessionId: { type: Number, required: true },
  },
  data () {
    const cfg = window.congressConfig || {}
    return {
      config: cfg,
      currentRound: 0,
      electionStarted: false,
      electionStatus: null,
      candidates: [],
      selectedCandidate: null,
      tallyResult: null,
      starting: false,
      voting: false,
      tallying: false,
      error: null,
    }
  },
  methods: {
    headers () {
      return {
        'Content-Type': 'application/json',
        'X-Congress-Api-Key': this.config.apiKey,
      }
    },
    async startElection () {
      this.starting = true
      this.error = null
      try {
        const resp = await fetch(
          `${this.config.nekocongressUrl}/api/congress/sessions/${this.sessionId}/po-election/start/`,
          { method: 'POST', headers: this.headers() }
        )
        if (!resp.ok) throw new Error((await resp.json()).detail)
        const data = await resp.json()
        this.currentRound = data.round_number
        this.electionStarted = true
        this.electionStatus = 'OPEN'
        this.candidates = data.candidates
        this.tallyResult = null
        this.selectedCandidate = null
      } catch (e) {
        this.error = e.message
      } finally {
        this.starting = false
      }
    },
    async castVote () {
      this.voting = true
      this.error = null
      try {
        const resp = await fetch(
          `${this.config.nekocongressUrl}/api/congress/sessions/${this.sessionId}/po-election/vote/`,
          {
            method: 'POST',
            headers: this.headers(),
            body: JSON.stringify({
              session_id: this.sessionId,
              voter_legislator_id: 0, // Will be set from auth context
              candidate_legislator_id: this.selectedCandidate,
            }),
          }
        )
        if (!resp.ok) throw new Error((await resp.json()).detail)
        this.selectedCandidate = null
      } catch (e) {
        this.error = e.message
      } finally {
        this.voting = false
      }
    },
    async tallyVotes () {
      this.tallying = true
      this.error = null
      try {
        const resp = await fetch(
          `${this.config.nekocongressUrl}/api/congress/sessions/${this.sessionId}/po-election/tally/`,
          { method: 'POST', headers: this.headers() }
        )
        if (!resp.ok) throw new Error((await resp.json()).detail)
        this.tallyResult = await resp.json()
        this.electionStatus = this.tallyResult.status
      } catch (e) {
        this.error = e.message
      } finally {
        this.tallying = false
      }
    },
  },
}
</script>
