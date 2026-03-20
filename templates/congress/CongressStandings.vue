<template>
  <div>
    <div class="card mb-3">
      <div class="card-header d-flex justify-content-between align-items-center">
        <strong>Congress Standings</strong>
        <div>
          <button class="btn btn-sm mr-1"
                  :class="view === 'tournament' ? 'btn-primary' : 'btn-outline-primary'"
                  @click="view = 'tournament'; loadTournamentStandings()">
            Overall
          </button>
          <button class="btn btn-sm"
                  :class="view === 'chamber' ? 'btn-primary' : 'btn-outline-primary'"
                  @click="view = 'chamber'">
            By Chamber
          </button>
        </div>
      </div>
    </div>

    <!-- Tournament-wide standings -->
    <div v-if="view === 'tournament'">
      <div class="card mb-3">
        <div class="card-body p-0">
          <table class="table table-sm table-hover mb-0">
            <thead class="thead-light">
              <tr>
                <th>#</th>
                <th>Legislator</th>
                <th>School</th>
                <th>Raw Pts</th>
                <th>Norm. Score</th>
                <th>Rank Avg</th>
                <th>Speeches</th>
                <th>PO Pts</th>
                <th v-if="showAdvancement">Adv.</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in tournamentStandings" :key="row.legislator_id"
                  :class="{ 'table-success': row.advancing }">
                <td>{{ idx + 1 }}</td>
                <td>{{ row.display_name }}</td>
                <td>{{ row.institution_name }}</td>
                <td>{{ row.total_raw_points }}</td>
                <td>{{ row.normalized_score != null ? row.normalized_score.toFixed(2) : '—' }}</td>
                <td>{{ row.average_rank != null ? row.average_rank.toFixed(2) : '—' }}</td>
                <td>{{ row.speech_count }}</td>
                <td>{{ row.po_points || '—' }}</td>
                <td v-if="showAdvancement">
                  <span v-if="row.advancing" class="badge badge-success">✓</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Advancement -->
      <div class="card mb-3" v-if="config.isDirector">
        <div class="card-header"><strong>Advancement</strong></div>
        <div class="card-body">
          <div class="form-inline mb-2">
            <label class="mr-2">Advance top</label>
            <input type="number" class="form-control form-control-sm mr-2" style="width:80px"
                   v-model.number="advanceCount" min="1" />
            <button class="btn btn-primary btn-sm" @click="computeAdvancement">
              Compute
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Chamber standings -->
    <div v-if="view === 'chamber'">
      <div class="form-group">
        <label>Select Chamber</label>
        <select class="form-control" v-model="selectedChamberId" @change="loadChamberStandings">
          <option :value="null">-- pick --</option>
          <option v-for="ch in chambers" :key="ch.id" :value="ch.id">
            {{ ch.name }}
          </option>
        </select>
      </div>

      <div class="card" v-if="chamberStandings.length">
        <div class="card-body p-0">
          <table class="table table-sm table-hover mb-0">
            <thead class="thead-light">
              <tr>
                <th>#</th>
                <th>Legislator</th>
                <th>Total Pts</th>
                <th>Rank Avg</th>
                <th>Speeches</th>
                <th>PO Pts</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in chamberStandings" :key="row.legislator_id">
                <td>{{ idx + 1 }}</td>
                <td>{{ row.display_name }}</td>
                <td>{{ row.total_raw_points }}</td>
                <td>{{ row.average_rank != null ? row.average_rank.toFixed(2) : '—' }}</td>
                <td>{{ row.speech_count }}</td>
                <td>{{ row.po_points || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="error" class="alert alert-danger mt-2">{{ error }}</div>
  </div>
</template>

<script>
export default {
  name: 'CongressStandings',
  data () {
    const cfg = window.congressConfig || {}
    return {
      config: cfg,
      congressTournamentId: null,
      view: 'tournament',
      tournamentStandings: [],
      chamberStandings: [],
      chambers: [],
      selectedChamberId: null,
      advanceCount: 8,
      showAdvancement: false,
      error: null,
    }
  },
  async mounted () {
    await this.resolveCongressTournament()
    if (this.congressTournamentId) {
      this.loadTournamentStandings()
      this.loadChambers()
    }
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
    async resolveCongressTournament () {
      try {
        const resp = await this.api(
          `/api/congress/tournaments/?tournament_id=${this.config.tournamentId}`
        )
        if (resp.ok) {
          const items = await resp.json()
          if (items.length) this.congressTournamentId = items[0].id
        }
      } catch (_) { /* ignore */ }
    },
    async loadChambers () {
      try {
        const resp = await this.api(
          `/api/congress/chambers/?congress_tournament_id=${this.congressTournamentId}`
        )
        if (resp.ok) this.chambers = await resp.json()
      } catch (_) { /* ignore */ }
    },
    async loadTournamentStandings () {
      this.error = null
      try {
        const resp = await this.api(
          `/api/congress/standings/tournament/${this.congressTournamentId}/`
        )
        if (!resp.ok) throw new Error((await resp.json()).detail)
        this.tournamentStandings = await resp.json()
        this.showAdvancement = false
      } catch (e) {
        this.error = e.message
      }
    },
    async loadChamberStandings () {
      if (!this.selectedChamberId) return
      this.error = null
      try {
        const resp = await this.api(
          `/api/congress/standings/chamber/${this.selectedChamberId}/`
        )
        if (!resp.ok) throw new Error((await resp.json()).detail)
        this.chamberStandings = await resp.json()
      } catch (e) {
        this.error = e.message
      }
    },
    async computeAdvancement () {
      this.error = null
      try {
        const resp = await this.api(
          `/api/congress/standings/tournament/${this.congressTournamentId}/advancement/`,
          {
            method: 'POST',
            body: JSON.stringify({ advance_count: this.advanceCount }),
          }
        )
        if (!resp.ok) throw new Error((await resp.json()).detail)
        this.tournamentStandings = await resp.json()
        this.showAdvancement = true
      } catch (e) {
        this.error = e.message
      }
    },
  },
}
</script>
