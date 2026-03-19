<template>
  <div class="card">
    <div class="card-body">
      <h5 class="card-title">
        Ballot — Room {{ roomNumber }}
        <small class="text-muted">Round {{ roundNumber }}</small>
      </h5>

      <div v-if="loading" class="text-center py-4">
        <span class="spinner-border text-primary"></span>
      </div>

      <div v-else>
        <table class="table table-sm table-bordered">
          <thead class="thead-light">
            <tr>
              <th>Competitor</th>
              <th>School</th>
              <th style="width:100px">Rank</th>
              <th style="width:120px">Speaker Pts</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in entries" :key="entry.entry_id"
                :class="{ 'table-danger': hasDuplicateRank(entry) }">
              <td>{{ entry.speaker_name }}</td>
              <td><small>{{ entry.institution_code }}</small></td>
              <td>
                <input v-model.number="entry.rank" type="number"
                       min="1" :max="entries.length"
                       class="form-control form-control-sm"
                       :class="{ 'is-invalid': hasDuplicateRank(entry) }" />
              </td>
              <td>
                <input v-model.number="entry.speaker_points" type="number"
                       min="0" max="30" step="0.5"
                       class="form-control form-control-sm" />
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="duplicateWarning" class="alert alert-warning py-1 px-2 small">
          ⚠ Duplicate ranks detected — each competitor must have a unique rank.
        </div>

        <div v-if="error" class="alert alert-danger py-1 px-2 small">{{ error }}</div>
        <div v-if="success" class="alert alert-success py-1 px-2 small">{{ success }}</div>

        <div class="d-flex justify-content-end">
          <button class="btn btn-primary btn-sm"
                  :disabled="!canSubmit || submitting"
                  @click="submitBallot">
            <span v-if="submitting" class="spinner-border spinner-border-sm mr-1"></span>
            Submit Ballot
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'IEBallotForm',
  props: {
    roomId: { type: Number, required: true },
  },
  data () {
    return {
      entries: [],
      roomNumber: null,
      roundNumber: null,
      loading: true,
      submitting: false,
      error: '',
      success: '',
    }
  },
  computed: {
    duplicateWarning () {
      var ranks = this.entries
        .map(function (e) { return e.rank })
        .filter(function (r) { return r != null && r > 0 })
      return ranks.length !== new Set(ranks).size
    },
    allRanksFilled () {
      return this.entries.every(function (e) {
        return e.rank != null && e.rank > 0 && e.speaker_points != null && e.speaker_points >= 0
      })
    },
    canSubmit () {
      return this.allRanksFilled && !this.duplicateWarning
    },
  },
  mounted () {
    this.fetchRoom()
  },
  methods: {
    hasDuplicateRank (entry) {
      if (!entry.rank) return false
      var count = this.entries.filter(function (e) {
        return e.rank === entry.rank
      }).length
      return count > 1
    },
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
        throw new Error('Cannot reach IE service. Is nekospeech running? (' + networkErr.message + ')')
      }

      if (!response.ok) {
        var detail = 'HTTP ' + response.status
        try {
          var errData = await response.json()
          detail = errData.detail || errData.message || detail
        } catch (_) {
          if (response.status === 403) detail = 'Authentication failed — check NEKOSPEECH_IE_API_KEY'
          else if (response.status === 404) detail = 'Endpoint not found — check NEKOSPEECH_URL'
          else if (response.status === 502) detail = 'IE service is down — check nekospeech on Heroku'
          else detail = 'Server error ' + response.status
        }
        throw new Error(detail)
      }

      return response.json()
    },
    async fetchRoom () {
      this.loading = true
      try {
        const cfg = window.ieConfig || {}
        const eventId = cfg.eventId || 0

        // First try to load existing results for this room (for editing)
        try {
          const data = await this.apiFetch('/ballots/' + this.roomId + '/')
          if (data && data.length > 0) {
            // Room already has results — load for editing
            this.entries = data.map(r => ({
              entry_id: r.entry_id,
              speaker_name: r.speaker_name || 'Entry #' + r.entry_id,
              institution_code: r.institution_code || '',
              rank: r.rank,
              speaker_points: r.speaker_points,
            }))
            this.loading = false
            return
          }
        } catch (_) {
          // No existing results or error — fall through to draw lookup
        }

        // No existing results — find the room by trying each round's draw
        // Try the round from config first, then scan event rounds
        const firstTry = cfg.roundNumber || 1
        const maxRounds = 10
        const roundsToTry = [firstTry]
        for (let r = 1; r <= maxRounds; r++) {
          if (r !== firstTry) roundsToTry.push(r)
        }

        let foundRoom = null
        for (const rn of roundsToTry) {
          try {
            const drawData = await this.apiFetch('/draw/' + eventId + '/round/' + rn + '/')
            const rooms = drawData.rooms || []
            const room = rooms.find(r => r.id === this.roomId)
            if (room) {
              foundRoom = room
              this.roundNumber = rn
              this.roomNumber = room.room_number
              break
            }
          } catch (_) {
            continue
          }
        }

        if (!foundRoom) {
          this.error = 'Room #' + this.roomId + ' not found in any round draw.'
          this.loading = false
          return
        }

        this.entries = (foundRoom.entries || []).map(e => ({
          entry_id: e.id,
          speaker_name: e.speaker_name || 'Entry #' + e.id,
          institution_code: e.institution_code || '',
          rank: null,
          speaker_points: null,
        }))

      } catch (err) {
        this.error = 'Failed to load room entries: ' + (err.message || err)
      } finally {
        this.loading = false
      }
    },
    async submitBallot () {
      this.submitting = true
      this.error = ''
      this.success = ''
      try {
        var payload = {
          room_id: this.roomId,
          results: this.entries.map(function (e) {
            return {
              entry_id: e.entry_id,
              rank: e.rank,
              speaker_points: e.speaker_points,
            }
          }),
        }
        var result = await this.apiFetch('/ballots/submit/', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        this.success = 'Ballot submitted successfully!'
        if (result.round_complete) {
          this.success += ' All rooms in this round are complete.'
        }
      } catch (e) {
        this.error = e.message
      } finally {
        this.submitting = false
      }
    },
  },
}
</script>
