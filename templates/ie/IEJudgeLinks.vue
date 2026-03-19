<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0">Judge Links — Round {{ roundNumber }}</h5>
      <button v-if="links.length > 0" class="btn btn-outline-primary btn-sm" @click="copyAll">
        {{ copiedAll ? '✓ Copied!' : 'Copy All Links' }}
      </button>
    </div>

    <div v-if="loading" class="text-center py-4">
      <span class="spinner-border spinner-border-sm mr-1"></span> Generating judge links...
    </div>

    <div v-else-if="error" class="alert alert-danger">{{ error }}</div>

    <div v-else-if="links.length === 0" class="alert alert-info">
      No judges assigned for this round yet. Assign judges in the draw first.
    </div>

    <div v-else>
      <div v-for="link in links" :key="link.room_id" class="card mb-2">
        <div class="card-body py-2 px-3">
          <div class="d-flex justify-content-between align-items-center">
            <div>
              <strong>Room {{ link.room_number }}</strong>
              <span class="mx-2">|</span>
              <span>{{ link.judge_name || 'Judge #' + link.judge_id }}</span>
            </div>
            <div>
              <button class="btn btn-outline-secondary btn-sm mr-1"
                      @click="copyLink(link)">
                {{ link.copied ? '✓' : 'Copy' }}
              </button>
              <a :href="link.ballot_url" target="_blank"
                 class="btn btn-outline-primary btn-sm">Open</a>
            </div>
          </div>
          <div class="mt-1">
            <code class="small text-break">{{ link.ballot_url }}</code>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'IEJudgeLinks',
  data () {
    return {
      links: [],
      loading: true,
      error: '',
      copiedAll: false,
    }
  },
  computed: {
    cfg () { return window.ieConfig || {} },
    eventId () { return this.cfg.eventId },
    roundNumber () { return this.cfg.roundNumber },
    pathPrefix () {
      return this.cfg.tournamentSlug ? ('/' + this.cfg.tournamentSlug) : ''
    },
  },
  mounted () {
    this.generateLinks()
  },
  methods: {
    async generateLinks () {
      this.loading = true
      this.error = ''
      try {
        var url = this.pathPrefix + '/admin/ie/' + this.eventId + '/judge-links/' + this.roundNumber + '/'
        var response = await fetch(url, {
          method: 'POST',
          headers: { 'X-CSRFToken': this.getCsrf(), 'Content-Type': 'application/json' },
          credentials: 'same-origin',
        })
        if (!response.ok) {
          var detail = 'HTTP ' + response.status
          try {
            var errData = await response.json()
            detail = errData.error || errData.detail || detail
          } catch (_) {}
          throw new Error(detail)
        }
        var data = await response.json()
        this.links = (data.links || []).map(function (l) {
          l.copied = false
          return l
        })
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
    getCsrf () {
      var match = document.cookie.match(/csrftoken=([^;]+)/)
      return match ? match[1] : ''
    },
    async copyLink (link) {
      try {
        await navigator.clipboard.writeText(link.ballot_url)
        link.copied = true
        var self = this
        setTimeout(function () { link.copied = false; self.$forceUpdate() }, 2000)
        this.$forceUpdate()
      } catch (_) {
        // Fallback: select text
        window.prompt('Copy this link:', link.ballot_url)
      }
    },
    async copyAll () {
      var text = this.links.map(function (l) {
        return 'Room ' + l.room_number + ' — ' + (l.judge_name || 'Judge') + '\n' + l.ballot_url
      }).join('\n\n')
      try {
        await navigator.clipboard.writeText(text)
        this.copiedAll = true
        var self = this
        setTimeout(function () { self.copiedAll = false }, 2000)
      } catch (_) {
        window.prompt('Copy all links:', text)
      }
    },
  },
}
</script>
