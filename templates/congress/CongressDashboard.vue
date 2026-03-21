<template>
  <div>
    <div class="card mb-3">
      <div class="card-header"><strong>Congressional Debate Dashboard</strong></div>
      <div class="card-body">
        <div class="row text-center">
          <div class="col-md-3">
            <div class="h3">{{ stats.chambers }}</div>
            <small class="text-muted">Chambers</small>
          </div>
          <div class="col-md-3">
            <div class="h3">{{ stats.legislators }}</div>
            <small class="text-muted">Legislators</small>
          </div>
          <div class="col-md-3">
            <div class="h3">{{ stats.sessions }}</div>
            <small class="text-muted">Sessions</small>
          </div>
          <div class="col-md-3">
            <div class="h3">{{ stats.legislation }}</div>
            <small class="text-muted">Legislation Items</small>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick links -->
    <div class="row">
      <div class="col-md-4 mb-3">
        <div class="card h-100">
          <div class="card-body">
            <h5 class="card-title">Setup</h5>
            <p class="card-text text-muted">Configure tournament parameters, scoring, and questioning rules.</p>
            <a :href="setupUrl" class="btn btn-primary btn-sm">Open Setup</a>
          </div>
        </div>
      </div>
      <div class="col-md-4 mb-3">
        <div class="card h-100">
          <div class="card-body">
            <h5 class="card-title">Docket</h5>
            <p class="card-text text-muted">Manage legislation items and assign them to sessions.</p>
            <a :href="docketUrl" class="btn btn-primary btn-sm">Manage Docket</a>
          </div>
        </div>
      </div>
      <div class="col-md-4 mb-3">
        <div class="card h-100">
          <div class="card-body">
            <h5 class="card-title">Chambers</h5>
            <p class="card-text text-muted">Create chambers and assign legislators.</p>
            <a :href="chambersUrl" class="btn btn-primary btn-sm">Manage Chambers</a>
          </div>
        </div>
      </div>
    </div>

    <div class="row">
      <div class="col-md-6 mb-3">
        <div class="card h-100">
          <div class="card-body">
            <h5 class="card-title">Standings</h5>
            <p class="card-text text-muted">View cross-chamber normalized standings and compute advancement.</p>
            <a :href="standingsUrl" class="btn btn-outline-primary btn-sm">View Standings</a>
          </div>
        </div>
      </div>
      <div class="col-md-6 mb-3">
        <div class="card h-100">
          <div class="card-body">
            <h5 class="card-title">Active Sessions</h5>
            <ul class="list-unstyled mb-0" v-if="activeSessions.length">
              <li v-for="s in activeSessions" :key="s.id" class="mb-1">
                <a :href="sessionUrl(s.id)">{{ s.chamber_name }} — Session {{ s.session_number }}</a>
                <span class="badge badge-success ml-1">Active</span>
              </li>
            </ul>
            <p class="text-muted mb-0" v-else>No active sessions.</p>
          </div>
        </div>
      </div>
    </div>

    <div v-if="error" class="alert alert-danger mt-2">{{ error }}</div>
  </div>
</template>

<script>
export default {
  name: 'CongressDashboard',
  data () {
    const cfg = window.congressConfig || {}
    const slug = cfg.tournamentSlug || ''
    return {
      config: cfg,
      stats: { chambers: 0, legislators: 0, sessions: 0, legislation: 0 },
      activeSessions: [],
      setupUrl: `/${slug}/admin/congress/setup/`,
      docketUrl: `/${slug}/admin/congress/docket/`,
      chambersUrl: `/${slug}/admin/congress/chambers/`,
      standingsUrl: `/${slug}/admin/congress/standings/`,
      error: null,
    }
  },
  mounted () {
    this.loadStats()
  },
  methods: {
    headers () {
      return { 'X-Congress-Api-Key': this.config.apiKey }
    },
    api (path) {
      return fetch(`${this.config.nekocongressUrl}${path}`, { headers: this.headers() })
    },
    sessionUrl (id) {
      return `/${this.config.tournamentSlug}/admin/congress/session/${id}/`
    },
    async loadStats () {
      try {
        // Load chambers
        const chResp = await this.api(
          `/api/congress/chambers/?tournament_id=${this.config.tournamentId}`
        )
        if (chResp.ok) {
          const chambers = await chResp.json()
          this.stats.chambers = chambers.length
        }

        // Load legislators
        const legResp = await this.api(
          `/api/congress/legislators/?tournament_id=${this.config.tournamentId}`
        )
        if (legResp.ok) {
          const legislators = await legResp.json()
          this.stats.legislators = legislators.length
        }

        // Load sessions (check for active ones)
        const sessResp = await this.api(
          `/api/congress/sessions/?tournament_id=${this.config.tournamentId}`
        )
        if (sessResp.ok) {
          const sessions = await sessResp.json()
          this.stats.sessions = sessions.length
          this.activeSessions = sessions.filter(s => s.status === 'ACTIVE')
        }

        // Load legislation count
        const legisResp = await this.api(
          `/api/congress/docket/legislation/?tournament_id=${this.config.tournamentId}`
        )
        if (legisResp.ok) {
          const items = await legisResp.json()
          this.stats.legislation = items.length
        }
      } catch (e) {
        this.error = e.message
      }
    },
  },
}
</script>
