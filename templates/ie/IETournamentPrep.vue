<template>
  <div>
    <!-- Tab Navigation -->
    <ul class="nav nav-tabs mb-3">
      <li class="nav-item">
        <a class="nav-link" :class="{ active: tab === 'institutions' }"
           href="#" @click.prevent="tab = 'institutions'">
          Schools <span class="badge badge-secondary">{{ institutions.length }}</span>
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" :class="{ active: tab === 'speakers' }"
           href="#" @click.prevent="tab = 'speakers'">
          Speakers <span class="badge badge-secondary">{{ speakers.length }}</span>
        </a>
      </li>
      <li class="nav-item">
        <a class="nav-link" :class="{ active: tab === 'judges' }"
           href="#" @click.prevent="tab = 'judges'">
          Judges <span class="badge badge-secondary">{{ judges.length }}</span>
        </a>
      </li>
    </ul>

    <!-- ─────────────── INSTITUTIONS TAB ─────────────── -->
    <div v-if="tab === 'institutions'">
      <div class="card mb-3">
        <div class="card-body">
          <h6 class="card-title">Add School</h6>
          <div class="row">
            <div class="col-md-5">
              <input v-model="instForm.name" class="form-control form-control-sm"
                     placeholder="Full name (e.g. Springfield High School)" />
            </div>
            <div class="col-md-3">
              <input v-model="instForm.code" class="form-control form-control-sm"
                     placeholder="Short code (e.g. SHS)" maxlength="20" />
            </div>
            <div class="col-md-2">
              <button class="btn btn-primary btn-sm btn-block" :disabled="!instForm.name || !instForm.code || saving"
                      @click="addInstitution">
                <span v-if="saving" class="spinner-border spinner-border-sm mr-1"></span>
                Add
              </button>
            </div>
            <div class="col-md-2">
              <button class="btn btn-outline-secondary btn-sm btn-block"
                      @click="showCsvImport = 'institutions'">
                CSV Import
              </button>
            </div>
          </div>
          <div v-if="instError" class="text-danger small mt-1">{{ instError }}</div>
        </div>
      </div>

      <!-- CSV Import Panel -->
      <div v-if="showCsvImport === 'institutions'" class="card mb-3 border-info">
        <div class="card-body">
          <h6 class="card-title">CSV Import — Schools</h6>
          <p class="small text-muted mb-2">
            Paste CSV with columns: <code>name, code</code> (one school per line, no header needed)
          </p>
          <textarea v-model="csvText" class="form-control form-control-sm mb-2"
                    rows="5" placeholder="Springfield High School, SHS&#10;Lincoln Academy, LA"></textarea>
          <button class="btn btn-info btn-sm mr-2" :disabled="!csvText.trim() || csvImporting"
                  @click="importCsv('institutions')">
            <span v-if="csvImporting" class="spinner-border spinner-border-sm mr-1"></span>
            Import
          </button>
          <button class="btn btn-outline-secondary btn-sm" @click="showCsvImport = null; csvText = ''">Cancel</button>
          <div v-if="csvResult" class="mt-2 small" :class="csvResult.error ? 'text-danger' : 'text-success'">
            {{ csvResult.message }}
          </div>
        </div>
      </div>

      <!-- Institutions Table -->
      <div v-if="loading" class="text-center py-3">
        <span class="spinner-border spinner-border-sm"></span> Loading...
      </div>
      <table v-else-if="institutions.length" class="table table-sm table-striped">
        <thead class="thead-light">
          <tr>
            <th>Name</th>
            <th>Code</th>
            <th style="width: 80px"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="inst in institutions" :key="inst.id">
            <td>{{ inst.name }}</td>
            <td><span class="badge badge-light">{{ inst.code }}</span></td>
            <td>
              <button class="btn btn-outline-danger btn-sm"
                      @click="deleteInstitution(inst)">×</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="alert alert-info">No schools added yet.</div>
    </div>

    <!-- ─────────────── SPEAKERS TAB ─────────────── -->
    <div v-if="tab === 'speakers'">
      <div class="card mb-3">
        <div class="card-body">
          <h6 class="card-title">Add Speaker</h6>
          <div class="row">
            <div class="col-md-4">
              <input v-model="spkForm.name" class="form-control form-control-sm"
                     placeholder="Speaker name" />
            </div>
            <div class="col-md-3">
              <select v-model="spkForm.institution_id" class="form-control form-control-sm">
                <option value="">— Select school —</option>
                <option v-for="inst in institutions" :key="inst.id" :value="inst.id">
                  {{ inst.code }} — {{ inst.name }}
                </option>
              </select>
            </div>
            <div class="col-md-3">
              <input v-model="spkForm.email" class="form-control form-control-sm"
                     placeholder="Email (optional)" type="email" />
            </div>
            <div class="col-md-2">
              <button class="btn btn-primary btn-sm btn-block" :disabled="!spkForm.name || saving"
                      @click="addSpeaker">
                <span v-if="saving" class="spinner-border spinner-border-sm mr-1"></span>
                Add
              </button>
            </div>
          </div>
          <div class="row mt-2">
            <div class="col-md-10"></div>
            <div class="col-md-2">
              <button class="btn btn-outline-secondary btn-sm btn-block"
                      @click="showCsvImport = 'speakers'">
                CSV Import
              </button>
            </div>
          </div>
          <div v-if="spkError" class="text-danger small mt-1">{{ spkError }}</div>
        </div>
      </div>

      <!-- CSV Import Panel -->
      <div v-if="showCsvImport === 'speakers'" class="card mb-3 border-info">
        <div class="card-body">
          <h6 class="card-title">CSV Import — Speakers</h6>
          <p class="small text-muted mb-2">
            Paste CSV with columns: <code>name, institution_code, email</code> (email optional, no header needed).
            Institution code must match an existing school.
          </p>
          <textarea v-model="csvText" class="form-control form-control-sm mb-2"
                    rows="5" placeholder="Alice Smith, SHS, alice@example.com&#10;Bob Jones, LA"></textarea>
          <button class="btn btn-info btn-sm mr-2" :disabled="!csvText.trim() || csvImporting"
                  @click="importCsv('speakers')">
            <span v-if="csvImporting" class="spinner-border spinner-border-sm mr-1"></span>
            Import
          </button>
          <button class="btn btn-outline-secondary btn-sm" @click="showCsvImport = null; csvText = ''">Cancel</button>
          <div v-if="csvResult" class="mt-2 small" :class="csvResult.error ? 'text-danger' : 'text-success'">
            {{ csvResult.message }}
          </div>
        </div>
      </div>

      <!-- Speakers Table -->
      <div v-if="loading" class="text-center py-3">
        <span class="spinner-border spinner-border-sm"></span> Loading...
      </div>
      <table v-else-if="speakers.length" class="table table-sm table-striped">
        <thead class="thead-light">
          <tr>
            <th>Name</th>
            <th>School</th>
            <th>Email</th>
            <th style="width: 80px"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="spk in speakers" :key="spk.id">
            <td>{{ spk.name }}</td>
            <td><span class="badge badge-light">{{ spk.institution_code || '—' }}</span></td>
            <td class="small text-muted">{{ spk.email || '' }}</td>
            <td>
              <button class="btn btn-outline-danger btn-sm"
                      @click="deleteSpeaker(spk)">×</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="alert alert-info">No speakers added yet. Add schools first, then add speakers.</div>
    </div>

    <!-- ─────────────── JUDGES TAB ─────────────── -->
    <div v-if="tab === 'judges'">
      <div class="card mb-3">
        <div class="card-body">
          <h6 class="card-title">Add Judge</h6>
          <div class="row">
            <div class="col-md-4">
              <input v-model="judgeForm.name" class="form-control form-control-sm"
                     placeholder="Judge name" />
            </div>
            <div class="col-md-3">
              <select v-model="judgeForm.institution_id" class="form-control form-control-sm">
                <option value="">— Select school (optional) —</option>
                <option v-for="inst in institutions" :key="inst.id" :value="inst.id">
                  {{ inst.code }} — {{ inst.name }}
                </option>
              </select>
            </div>
            <div class="col-md-3">
              <input v-model="judgeForm.email" class="form-control form-control-sm"
                     placeholder="Email (optional)" type="email" />
            </div>
            <div class="col-md-2">
              <button class="btn btn-primary btn-sm btn-block" :disabled="!judgeForm.name || saving"
                      @click="addJudge">
                <span v-if="saving" class="spinner-border spinner-border-sm mr-1"></span>
                Add
              </button>
            </div>
          </div>
          <div class="row mt-2">
            <div class="col-md-10"></div>
            <div class="col-md-2">
              <button class="btn btn-outline-secondary btn-sm btn-block"
                      @click="showCsvImport = 'judges'">
                CSV Import
              </button>
            </div>
          </div>
          <div v-if="judgeError" class="text-danger small mt-1">{{ judgeError }}</div>
        </div>
      </div>

      <!-- CSV Import Panel -->
      <div v-if="showCsvImport === 'judges'" class="card mb-3 border-info">
        <div class="card-body">
          <h6 class="card-title">CSV Import — Judges</h6>
          <p class="small text-muted mb-2">
            Paste CSV with columns: <code>name, institution_code, email</code> (institution and email optional, no header needed)
          </p>
          <textarea v-model="csvText" class="form-control form-control-sm mb-2"
                    rows="5" placeholder="Judge Alice, SHS&#10;Judge Bob, LA, bob@example.com"></textarea>
          <button class="btn btn-info btn-sm mr-2" :disabled="!csvText.trim() || csvImporting"
                  @click="importCsv('judges')">
            <span v-if="csvImporting" class="spinner-border spinner-border-sm mr-1"></span>
            Import
          </button>
          <button class="btn btn-outline-secondary btn-sm" @click="showCsvImport = null; csvText = ''">Cancel</button>
          <div v-if="csvResult" class="mt-2 small" :class="csvResult.error ? 'text-danger' : 'text-success'">
            {{ csvResult.message }}
          </div>
        </div>
      </div>

      <!-- Judges Table -->
      <div v-if="loading" class="text-center py-3">
        <span class="spinner-border spinner-border-sm"></span> Loading...
      </div>
      <table v-else-if="judges.length" class="table table-sm table-striped">
        <thead class="thead-light">
          <tr>
            <th>Name</th>
            <th>School</th>
            <th>Email</th>
            <th style="width: 80px"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="j in judges" :key="j.id">
            <td>{{ j.name }}</td>
            <td><span class="badge badge-light">{{ j.institution_code || 'Independent' }}</span></td>
            <td class="small text-muted">{{ j.email || '' }}</td>
            <td>
              <button class="btn btn-outline-danger btn-sm"
                      @click="deleteJudge(j)">×</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="alert alert-info">No judges added yet.</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'IETournamentPrep',
  data: function () {
    return {
      tab: 'institutions',
      loading: true,
      saving: false,
      institutions: [],
      speakers: [],
      judges: [],
      // Forms
      instForm: { name: '', code: '' },
      instError: '',
      spkForm: { name: '', institution_id: '', email: '' },
      spkError: '',
      judgeForm: { name: '', institution_id: '', email: '' },
      judgeError: '',
      // CSV
      showCsvImport: null,
      csvText: '',
      csvImporting: false,
      csvResult: null,
    }
  },
  computed: {
    baseUrl: function () {
      var cfg = window.ieConfig || {}
      var slug = cfg.tournamentSlug || ''
      return slug ? ('/' + slug + '/admin/ie/prep/') : '/admin/ie/prep/'
    },
  },
  mounted: function () {
    this.fetchAll()
  },
  methods: {
    csrfToken: function () {
      var match = document.cookie.match(/csrftoken=([^;]+)/)
      return match ? match[1] : ''
    },
    async djFetch (path, options) {
      options = options || {}
      var headers = Object.assign({
        'X-CSRFToken': this.csrfToken(),
      }, options.headers || {})
      if (options.body) headers['Content-Type'] = 'application/json'
      var response
      try {
        response = await fetch(this.baseUrl + path, Object.assign({}, options, { headers: headers }))
      } catch (err) {
        throw new Error('Network error: ' + err.message)
      }
      if (!response.ok) {
        var detail = 'HTTP ' + response.status
        try {
          var errData = await response.json()
          detail = errData.error || detail
        } catch (_) {}
        throw new Error(detail)
      }
      if (response.status === 204) return null
      return response.json()
    },
    async fetchAll () {
      this.loading = true
      try {
        var data = await this.djFetch('all/')
        this.institutions = data.institutions || []
        this.speakers = data.speakers || []
        this.judges = data.judges || []
      } catch (e) {
        // silently fail — empty lists
      } finally {
        this.loading = false
      }
    },
    // ──── Institutions ────
    async addInstitution () {
      this.instError = ''
      this.saving = true
      try {
        var inst = await this.djFetch('institutions/', {
          method: 'POST',
          body: JSON.stringify({ name: this.instForm.name.trim(), code: this.instForm.code.trim() }),
        })
        this.institutions.push(inst)
        this.instForm = { name: '', code: '' }
      } catch (e) {
        this.instError = e.message
      } finally {
        this.saving = false
      }
    },
    async deleteInstitution (inst) {
      if (!confirm('Delete "' + inst.name + '"? Speakers and judges from this school will keep their current data.')) return
      try {
        await this.djFetch('institutions/' + inst.id + '/', { method: 'DELETE' })
        this.institutions = this.institutions.filter(function (i) { return i.id !== inst.id })
      } catch (e) {
        alert(e.message)
      }
    },
    // ──── Speakers ────
    async addSpeaker () {
      this.spkError = ''
      this.saving = true
      try {
        var spk = await this.djFetch('speakers/', {
          method: 'POST',
          body: JSON.stringify({
            name: this.spkForm.name.trim(),
            institution_id: this.spkForm.institution_id || null,
            email: this.spkForm.email.trim() || null,
          }),
        })
        this.speakers.push(spk)
        this.spkForm = { name: '', institution_id: this.spkForm.institution_id, email: '' }
      } catch (e) {
        this.spkError = e.message
      } finally {
        this.saving = false
      }
    },
    async deleteSpeaker (spk) {
      if (!confirm('Delete speaker "' + spk.name + '"?')) return
      try {
        await this.djFetch('speakers/' + spk.id + '/', { method: 'DELETE' })
        this.speakers = this.speakers.filter(function (s) { return s.id !== spk.id })
      } catch (e) {
        alert(e.message)
      }
    },
    // ──── Judges ────
    async addJudge () {
      this.judgeError = ''
      this.saving = true
      try {
        var j = await this.djFetch('judges/', {
          method: 'POST',
          body: JSON.stringify({
            name: this.judgeForm.name.trim(),
            institution_id: this.judgeForm.institution_id || null,
            email: this.judgeForm.email.trim() || null,
          }),
        })
        this.judges.push(j)
        this.judgeForm = { name: '', institution_id: this.judgeForm.institution_id, email: '' }
      } catch (e) {
        this.judgeError = e.message
      } finally {
        this.saving = false
      }
    },
    async deleteJudge (j) {
      if (!confirm('Delete judge "' + j.name + '"?')) return
      try {
        await this.djFetch('judges/' + j.id + '/', { method: 'DELETE' })
        this.judges = this.judges.filter(function (jj) { return jj.id !== j.id })
      } catch (e) {
        alert(e.message)
      }
    },
    // ──── CSV Import ────
    async importCsv (type) {
      this.csvImporting = true
      this.csvResult = null
      try {
        var result = await this.djFetch('import/', {
          method: 'POST',
          body: JSON.stringify({ type: type, csv: this.csvText }),
        })
        this.csvResult = { error: false, message: result.message || 'Import complete.' }
        this.csvText = ''
        this.showCsvImport = null
        await this.fetchAll()
      } catch (e) {
        this.csvResult = { error: true, message: e.message }
      } finally {
        this.csvImporting = false
      }
    },
  },
}
</script>
