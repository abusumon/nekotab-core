<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0">Docket Management</h5>
      <button class="btn btn-primary btn-sm" @click="showAdd = !showAdd">
        {{ showAdd ? 'Cancel' : '+ Add Legislation' }}
      </button>
    </div>

    <!-- Add Legislation Form -->
    <div v-if="showAdd" class="card mb-3">
      <div class="card-body">
        <div class="row">
          <div class="col-md-2 form-group">
            <label class="font-weight-bold">Code</label>
            <input v-model="newLeg.docket_code" class="form-control form-control-sm"
                   placeholder="HB-1" />
          </div>
          <div class="col-md-4 form-group">
            <label class="font-weight-bold">Title</label>
            <input v-model="newLeg.title" class="form-control form-control-sm"
                   placeholder="A Bill to Reform..." />
          </div>
          <div class="col-md-2 form-group">
            <label class="font-weight-bold">Type</label>
            <select v-model="newLeg.legislation_type" class="form-control form-control-sm">
              <option value="BILL">Bill</option>
              <option value="RESOLUTION">Resolution</option>
            </select>
          </div>
          <div class="col-md-2 form-group">
            <label class="font-weight-bold">Category</label>
            <input v-model="newLeg.category" class="form-control form-control-sm"
                   placeholder="Education" />
          </div>
          <div class="col-md-2 form-group d-flex align-items-end">
            <button class="btn btn-success btn-sm btn-block" :disabled="!canAdd" @click="addLegislation">
              Add
            </button>
          </div>
        </div>
        <div class="form-group">
          <label class="font-weight-bold">Full Text (optional)</label>
          <textarea v-model="newLeg.full_text" class="form-control form-control-sm" rows="3"></textarea>
        </div>
      </div>
    </div>

    <!-- Legislation List -->
    <div v-if="loading" class="text-center py-3">
      <span class="spinner-border spinner-border-sm"></span> Loading…
    </div>
    <table v-else class="table table-sm table-hover">
      <thead class="thead-light">
        <tr>
          <th>Code</th>
          <th>Title</th>
          <th>Type</th>
          <th>Category</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="leg in legislation" :key="leg.id">
          <td><strong>{{ leg.docket_code }}</strong></td>
          <td>{{ leg.title }}</td>
          <td><span class="badge" :class="leg.legislation_type === 'BILL' ? 'badge-info' : 'badge-warning'">
            {{ leg.legislation_type }}
          </span></td>
          <td>{{ leg.category || '—' }}</td>
          <td>
            <button class="btn btn-outline-secondary btn-sm" @click="editLeg(leg)">Edit</button>
          </td>
        </tr>
        <tr v-if="legislation.length === 0">
          <td colspan="5" class="text-center text-muted">No legislation added yet.</td>
        </tr>
      </tbody>
    </table>

    <div v-if="error" class="alert alert-danger mt-2">{{ error }}</div>
  </div>
</template>

<script>
export default {
  name: 'CongressDocketManager',
  data () {
    const cfg = window.congressConfig || {}
    return {
      config: cfg,
      loading: true,
      error: null,
      showAdd: false,
      legislation: [],
      congressTournamentId: null,
      newLeg: {
        docket_code: '',
        title: '',
        legislation_type: 'BILL',
        category: '',
        full_text: '',
      },
    }
  },
  computed: {
    canAdd () {
      return this.newLeg.docket_code && this.newLeg.title && this.congressTournamentId
    },
  },
  async mounted () {
    await this.fetchCongressTournament()
    await this.fetchLegislation()
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
        const url = `${this.config.nekocongressUrl}/api/congress/tournaments/?tournament_id=${this.config.tournamentId}`
        const resp = await fetch(url, { headers: this.headers() })
        const data = await resp.json()
        if (data.length > 0) {
          this.congressTournamentId = data[0].id
        }
      } catch (e) {
        this.error = e.message
      }
    },
    async fetchLegislation () {
      this.loading = true
      try {
        const url = `${this.config.nekocongressUrl}/api/congress/docket/legislation/?tournament_id=${this.config.tournamentId}`
        const resp = await fetch(url, { headers: this.headers() })
        this.legislation = await resp.json()
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
    async addLegislation () {
      this.error = null
      try {
        const url = `${this.config.nekocongressUrl}/api/congress/docket/legislation/`
        const resp = await fetch(url, {
          method: 'POST',
          headers: this.headers(),
          body: JSON.stringify({
            ...this.newLeg,
            congress_tournament_id: this.congressTournamentId,
          }),
        })
        if (!resp.ok) {
          const data = await resp.json()
          throw new Error(data.detail || `HTTP ${resp.status}`)
        }
        this.newLeg = { docket_code: '', title: '', legislation_type: 'BILL', category: '', full_text: '' }
        this.showAdd = false
        await this.fetchLegislation()
      } catch (e) {
        this.error = e.message
      }
    },
    editLeg (leg) {
      // For now, open inline edit mode (can be expanded)
      const newTitle = window.prompt('Edit title:', leg.title)
      if (newTitle && newTitle !== leg.title) {
        this.updateLegislation(leg.id, { title: newTitle })
      }
    },
    async updateLegislation (id, updates) {
      try {
        const url = `${this.config.nekocongressUrl}/api/congress/docket/legislation/${id}/`
        await fetch(url, {
          method: 'PATCH',
          headers: this.headers(),
          body: JSON.stringify(updates),
        })
        await this.fetchLegislation()
      } catch (e) {
        this.error = e.message
      }
    },
  },
}
</script>
