<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0">Chamber Assignment</h5>
      <button class="btn btn-primary btn-sm" @click="showCreate = !showCreate">
        {{ showCreate ? 'Cancel' : '+ Create Chamber' }}
      </button>
    </div>

    <!-- Create Chamber -->
    <div v-if="showCreate" class="card mb-3">
      <div class="card-body">
        <div class="row">
          <div class="col-md-4 form-group">
            <label class="font-weight-bold">Label</label>
            <input v-model="newChamber.label" class="form-control form-control-sm"
                   placeholder="Chamber A" />
          </div>
          <div class="col-md-3 form-group">
            <label class="font-weight-bold">Type</label>
            <select v-model="newChamber.chamber_type" class="form-control form-control-sm">
              <option value="HOUSE">House</option>
              <option value="SENATE">Senate</option>
            </select>
          </div>
          <div class="col-md-2 form-group">
            <label class="font-weight-bold">Number</label>
            <input v-model.number="newChamber.chamber_number" type="number" min="1"
                   class="form-control form-control-sm" />
          </div>
          <div class="col-md-3 form-group d-flex align-items-end">
            <button class="btn btn-success btn-sm btn-block" :disabled="!newChamber.label" @click="createChamber">
              Create
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Chambers -->
    <div v-if="loading" class="text-center py-3">
      <span class="spinner-border spinner-border-sm"></span> Loading…
    </div>

    <div v-else class="row">
      <div v-for="chamber in chambers" :key="chamber.id" class="col-md-6 mb-3">
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <strong>{{ chamber.label }}</strong>
            <span class="badge badge-secondary">{{ chamber.legislator_count }} legislators</span>
          </div>
          <div class="card-body">
            <p class="text-muted mb-2">
              Type: {{ chamber.chamber_type }} · Sessions: {{ chamber.session_count }}
            </p>

            <!-- Assign Legislators -->
            <div class="mb-2">
              <select v-model="selectedLegislators[chamber.id]" multiple
                      class="form-control form-control-sm" style="height: 100px;">
                <option v-for="leg in unassignedLegislators" :key="leg.id" :value="leg.id">
                  {{ leg.display_name }} ({{ leg.institution_code || '—' }})
                </option>
              </select>
            </div>
            <button class="btn btn-outline-primary btn-sm"
                    :disabled="!selectedLegislators[chamber.id] || selectedLegislators[chamber.id].length === 0"
                    @click="assignLegislators(chamber.id)">
              Assign Selected
            </button>

            <!-- Seating Chart -->
            <div v-if="seatingCharts[chamber.id]" class="mt-2">
              <table class="table table-sm table-bordered">
                <thead>
                  <tr>
                    <th>Seat</th>
                    <th>Legislator</th>
                    <th>School</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="a in seatingCharts[chamber.id]" :key="a.id">
                    <td>{{ a.seat_number }}</td>
                    <td>{{ a.legislator_name }}</td>
                    <td>{{ a.institution_code }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <button class="btn btn-outline-info btn-sm mt-1" @click="fetchSeating(chamber.id)">
              View Seating Chart
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="error" class="alert alert-danger mt-2">{{ error }}</div>
  </div>
</template>

<script>
export default {
  name: 'CongressChamberAssignment',
  data () {
    const cfg = window.congressConfig || {}
    return {
      config: cfg,
      loading: true,
      error: null,
      showCreate: false,
      chambers: [],
      legislators: [],
      assignedLegislatorIds: new Set(),
      selectedLegislators: {},
      seatingCharts: {},
      congressTournamentId: null,
      newChamber: {
        label: '',
        chamber_type: 'HOUSE',
        chamber_number: 1,
      },
    }
  },
  computed: {
    unassignedLegislators () {
      return this.legislators.filter(l => !this.assignedLegislatorIds.has(l.id))
    },
  },
  async mounted () {
    await this.fetchCongressTournament()
    await Promise.all([this.fetchChambers(), this.fetchLegislators()])
  },
  methods: {
    headers () {
      return {
        'Content-Type': 'application/json',
        'X-Congress-Api-Key': this.config.apiKey,
      }
    },
    async fetchCongressTournament () {
      try {
        const resp = await fetch(
          `${this.config.nekocongressUrl}/api/congress/tournaments/?tournament_id=${this.config.tournamentId}`,
          { headers: this.headers() }
        )
        const data = await resp.json()
        if (data.length > 0) this.congressTournamentId = data[0].id
      } catch (e) {
        this.error = e.message
      }
    },
    async fetchChambers () {
      this.loading = true
      try {
        const resp = await fetch(
          `${this.config.nekocongressUrl}/api/congress/chambers/?tournament_id=${this.config.tournamentId}`,
          { headers: this.headers() }
        )
        this.chambers = await resp.json()
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
    async fetchLegislators () {
      try {
        const resp = await fetch(
          `${this.config.nekocongressUrl}/api/congress/legislators/?tournament_id=${this.config.tournamentId}`,
          { headers: this.headers() }
        )
        this.legislators = await resp.json()
      } catch (e) {
        this.error = e.message
      }
    },
    async createChamber () {
      this.error = null
      try {
        const resp = await fetch(
          `${this.config.nekocongressUrl}/api/congress/chambers/`,
          {
            method: 'POST',
            headers: this.headers(),
            body: JSON.stringify({
              ...this.newChamber,
              congress_tournament_id: this.congressTournamentId,
            }),
          }
        )
        if (!resp.ok) throw new Error((await resp.json()).detail)
        this.showCreate = false
        this.newChamber = { label: '', chamber_type: 'HOUSE', chamber_number: this.chambers.length + 2 }
        await this.fetchChambers()
      } catch (e) {
        this.error = e.message
      }
    },
    async assignLegislators (chamberId) {
      const ids = this.selectedLegislators[chamberId]
      if (!ids || ids.length === 0) return
      this.error = null
      try {
        const resp = await fetch(
          `${this.config.nekocongressUrl}/api/congress/chambers/${chamberId}/assign-legislators/`,
          {
            method: 'POST',
            headers: this.headers(),
            body: JSON.stringify({ legislator_ids: ids }),
          }
        )
        if (!resp.ok) throw new Error((await resp.json()).detail)
        ids.forEach(id => this.assignedLegislatorIds.add(id))
        this.$set(this.selectedLegislators, chamberId, [])
        await this.fetchChambers()
      } catch (e) {
        this.error = e.message
      }
    },
    async fetchSeating (chamberId) {
      try {
        const resp = await fetch(
          `${this.config.nekocongressUrl}/api/congress/chambers/${chamberId}/seating-chart/`,
          { headers: this.headers() }
        )
        const data = await resp.json()
        this.$set(this.seatingCharts, chamberId, data.assignments)
      } catch (e) {
        this.error = e.message
      }
    },
  },
}
</script>
