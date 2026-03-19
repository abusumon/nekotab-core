<template>
  <div>
    <!-- Header -->
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div>
        <h5 class="mb-0">{{ eventName }} — Entries</h5>
        <small class="text-muted">
          {{ activeCount }} active{{ scratchedCount ? ' · ' + scratchedCount + ' scratched' : '' }}
        </small>
      </div>
      <button class="btn btn-sm"
              :class="showAdd ? 'btn-outline-secondary' : 'btn-primary'"
              @click="showAdd = !showAdd">
        {{ showAdd ? 'Close' : '+ Add Entries' }}
      </button>
    </div>

    <!-- Add Entries Panel -->
    <div v-if="showAdd" class="card mb-3">
      <div class="card-body">
        <!-- Solo / DUO toggle -->
        <div v-if="isDuo" class="mb-2">
          <span class="badge badge-info">DUO Event — select two speakers per entry</span>
        </div>

        <!-- Search bar -->
        <div class="form-group mb-2">
          <label class="font-weight-bold small">Search Speaker</label>
          <input v-model="searchQuery" class="form-control form-control-sm"
                 placeholder="Type a name..." @input="onSearch" />
        </div>

        <!-- Institution filter -->
        <div class="form-group mb-2">
          <label class="font-weight-bold small">Filter by School</label>
          <select v-model="filterInstitution" class="form-control form-control-sm" @change="onSearch">
            <option :value="null">All Schools</option>
            <option v-for="inst in institutions" :key="inst.id" :value="inst.id">
              {{ inst.name }} ({{ inst.code }})
            </option>
          </select>
        </div>

        <!-- Search results -->
        <div v-if="searching" class="text-muted small py-1">
          <span class="spinner-border spinner-border-sm mr-1"></span> Searching...
        </div>
        <div v-else-if="searchResults.length > 0" class="mb-2">
          <table class="table table-sm table-hover mb-0">
            <thead class="thead-light">
              <tr>
                <th v-if="isDuo" style="width:40px"></th>
                <th>Name</th>
                <th>School</th>
                <th style="width:100px"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="sp in searchResults" :key="sp.id">
                <td v-if="isDuo">
                  <input type="checkbox" :value="sp.id"
                         v-model="duoSelection"
                         :disabled="duoSelection.length >= 2 && duoSelection.indexOf(sp.id) === -1" />
                </td>
                <td>{{ sp.name }}</td>
                <td><small class="text-muted">{{ sp.institution }} ({{ sp.institution_code }})</small></td>
                <td v-if="!isDuo">
                  <button class="btn btn-outline-primary btn-sm" @click="addSolo(sp)"
                          :disabled="addingId === sp.id">
                    <span v-if="addingId === sp.id" class="spinner-border spinner-border-sm"></span>
                    {{ addingId === sp.id ? '' : 'Add' }}
                  </button>
                </td>
                <td v-else></td>
              </tr>
            </tbody>
          </table>
          <div v-if="isDuo && duoSelection.length === 2" class="mt-2">
            <button class="btn btn-primary btn-sm" :disabled="addingDuo" @click="addDuoPair">
              <span v-if="addingDuo" class="spinner-border spinner-border-sm mr-1"></span>
              Add DUO Pair
            </button>
          </div>
        </div>
        <div v-else-if="searchQuery.length >= 1 && !searching" class="text-muted small">
          No matching speakers found.
        </div>

        <!-- Bulk add from institution -->
        <hr class="my-2" />
        <div class="form-inline">
          <label class="font-weight-bold small mr-2">Add all from school:</label>
          <select v-model="bulkInstitution" class="form-control form-control-sm mr-2">
            <option :value="null">— Select —</option>
            <option v-for="inst in institutions" :key="inst.id" :value="inst.id">
              {{ inst.name }} ({{ inst.code }})
            </option>
          </select>
          <button class="btn btn-outline-primary btn-sm"
                  :disabled="!bulkInstitution || bulkAdding"
                  @click="bulkAddFromSchool">
            <span v-if="bulkAdding" class="spinner-border spinner-border-sm mr-1"></span>
            Add All
          </button>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-4">
      <span class="spinner-border spinner-border-sm mr-1"></span> Loading entries...
    </div>

    <!-- Entries Table -->
    <div v-else-if="entries.length === 0" class="alert alert-info">
      No entries yet. Click "+ Add Entries" to register speakers.
    </div>
    <table v-else class="table table-sm table-hover">
      <thead class="thead-light">
        <tr>
          <th style="width:50px">#</th>
          <th>Name</th>
          <th>School</th>
          <th>Status</th>
          <th style="width:120px">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(entry, idx) in sortedEntries" :key="entry.id"
            :class="{ 'text-muted': entry.scratch_status === 'SCRATCHED' }">
          <td>{{ idx + 1 }}</td>
          <td :class="{ 'text-decoration-line-through': entry.scratch_status === 'SCRATCHED' }">
            {{ entry.speaker_name }}
            <span v-if="entry.partner_id" class="text-muted"> + Partner</span>
          </td>
          <td>
            <small>{{ entry.institution_name }} ({{ entry.institution_code }})</small>
          </td>
          <td>
            <span class="badge" :class="entry.scratch_status === 'ACTIVE' ? 'badge-success' : 'badge-secondary'">
              {{ entry.scratch_status }}
            </span>
          </td>
          <td>
            <button v-if="entry.scratch_status === 'ACTIVE'"
                    class="btn btn-outline-warning btn-sm"
                    :disabled="actionId === entry.id"
                    @click="scratchEntry(entry)">
              Scratch
            </button>
            <button v-else
                    class="btn btn-outline-success btn-sm"
                    :disabled="actionId === entry.id"
                    @click="restoreEntry(entry)">
              Restore
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
export default {
  name: 'IEEntryManager',
  data () {
    return {
      entries: [],
      institutions: [],
      searchResults: [],
      searchQuery: '',
      filterInstitution: null,
      bulkInstitution: null,
      duoSelection: [],
      loading: true,
      searching: false,
      addingId: null,
      addingDuo: false,
      bulkAdding: false,
      actionId: null,
      showAdd: false,
      error: '',
      searchTimer: null,
    }
  },
  computed: {
    cfg () { return window.ieConfig || {} },
    eventId () { return this.cfg.eventId },
    eventName () { return this.cfg.eventName || 'Event' },
    eventType () { return this.cfg.eventType || '' },
    isDuo () { return this.eventType === 'DUO' },
    activeCount () { return this.entries.filter(function (e) { return e.scratch_status === 'ACTIVE' }).length },
    scratchedCount () { return this.entries.filter(function (e) { return e.scratch_status === 'SCRATCHED' }).length },
    sortedEntries () {
      return this.entries.slice().sort(function (a, b) {
        if (a.scratch_status !== b.scratch_status) return a.scratch_status === 'ACTIVE' ? -1 : 1
        return a.id - b.id
      })
    },
  },
  mounted () {
    this.fetchEntries()
    this.fetchInstitutions()
  },
  methods: {
    apiBase () {
      var cfg = window.ieConfig || {}
      return (window.NEKOSPEECH_URL || cfg.apiBaseUrl || '/api/ie').replace(/\/$/, '')
    },
    async apiFetch (url, options) {
      options = options || {}
      var cfg = window.ieConfig || {}
      var headers = Object.assign({}, options.headers || {})
      if (cfg.apiKey) headers['X-IE-Api-Key'] = cfg.apiKey
      if (options.body) headers['Content-Type'] = 'application/json'

      var response
      try {
        response = await fetch(this.apiBase() + url, Object.assign({}, options, { headers: headers }))
      } catch (networkErr) {
        throw new Error('Cannot reach IE service. (' + networkErr.message + ')')
      }

      if (!response.ok) {
        var detail = 'HTTP ' + response.status
        try {
          var errData = await response.json()
          detail = errData.detail || errData.message || detail
        } catch (_) {}
        throw new Error(detail)
      }

      if (response.status === 204) return null
      return response.json()
    },
    async fetchEntries () {
      this.loading = true
      this.error = ''
      try {
        this.entries = await this.apiFetch('/entries/?event_id=' + this.eventId)
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
    async fetchInstitutions () {
      try {
        this.institutions = await this.apiFetch('/entries/institutions/?tournament_id=' + this.cfg.tournamentId)
      } catch (_) { /* optional — page still works without it */ }
    },
    onSearch () {
      var self = this
      clearTimeout(this.searchTimer)
      if (this.searchQuery.length < 1 && !this.filterInstitution) {
        this.searchResults = []
        return
      }
      this.searchTimer = setTimeout(function () { self.doSearch() }, 300)
    },
    async doSearch () {
      this.searching = true
      try {
        var url = '/entries/search/?event_id=' + this.eventId + '&q=' + encodeURIComponent(this.searchQuery)
        if (this.filterInstitution) url += '&institution_id=' + this.filterInstitution
        this.searchResults = await this.apiFetch(url)
      } catch (e) {
        this.error = e.message
      } finally {
        this.searching = false
      }
    },
    async addSolo (speaker) {
      this.addingId = speaker.id
      this.error = ''
      try {
        await this.apiFetch('/entries/', {
          method: 'POST',
          body: JSON.stringify({ event_id: this.eventId, speaker_id: speaker.id }),
        })
        await this.fetchEntries()
        // Remove from search results
        this.searchResults = this.searchResults.filter(function (s) { return s.id !== speaker.id })
      } catch (e) {
        this.error = e.message
      } finally {
        this.addingId = null
      }
    },
    async addDuoPair () {
      if (this.duoSelection.length !== 2) return
      this.addingDuo = true
      this.error = ''
      try {
        await this.apiFetch('/entries/', {
          method: 'POST',
          body: JSON.stringify({
            event_id: this.eventId,
            speaker_id: this.duoSelection[0],
            partner_id: this.duoSelection[1],
          }),
        })
        this.duoSelection = []
        await this.fetchEntries()
        this.doSearch()
      } catch (e) {
        this.error = e.message
      } finally {
        this.addingDuo = false
      }
    },
    async bulkAddFromSchool () {
      this.bulkAdding = true
      this.error = ''
      try {
        // Get all speakers from this institution not yet registered
        var speakers = await this.apiFetch(
          '/entries/search/?event_id=' + this.eventId + '&institution_id=' + this.bulkInstitution
        )
        if (speakers.length === 0) {
          this.error = 'No unregistered speakers found from this school.'
          return
        }
        var bulkEntries = speakers.map(function (sp) {
          return { event_id: 0, speaker_id: sp.id }
        })
        await this.apiFetch('/entries/bulk/', {
          method: 'POST',
          body: JSON.stringify({ event_id: this.eventId, entries: bulkEntries }),
        })
        await this.fetchEntries()
        this.doSearch()
      } catch (e) {
        this.error = e.message
      } finally {
        this.bulkAdding = false
      }
    },
    async scratchEntry (entry) {
      this.actionId = entry.id
      this.error = ''
      try {
        await this.apiFetch('/entries/' + entry.id + '/', { method: 'DELETE' })
        entry.scratch_status = 'SCRATCHED'
      } catch (e) {
        this.error = e.message
      } finally {
        this.actionId = null
      }
    },
    async restoreEntry (entry) {
      this.actionId = entry.id
      this.error = ''
      try {
        await this.apiFetch('/entries/' + entry.id + '/restore/', { method: 'PATCH' })
        entry.scratch_status = 'ACTIVE'
      } catch (e) {
        this.error = e.message
      } finally {
        this.actionId = null
      }
    },
  },
}
</script>
