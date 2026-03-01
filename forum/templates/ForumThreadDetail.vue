<template>
  <div class="forum-thread-detail">
    <!-- Global Error Banner -->
    <div v-if="globalError" class="alert alert-danger alert-dismissible fade show" role="alert">
      {{ globalError }}
      <button type="button" class="close" @click="globalError = null" aria-label="Close">
        <span aria-hidden="true">&times;</span>
      </button>
    </div>

    <!-- Success Toast -->
    <div v-if="successMsg" class="alert alert-success alert-dismissible fade show" role="alert">
      {{ successMsg }}
      <button type="button" class="close" @click="successMsg = null" aria-label="Close">
        <span aria-hidden="true">&times;</span>
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
    </div>

    <div v-else-if="thread">
      <!-- Thread Header Card -->
      <div class="card mb-4">
        <div class="card-body">
          <div class="d-flex flex-wrap mb-2" style="gap: 6px;">
            <span v-if="thread.is_pinned" class="badge badge-warning">📌 Pinned</span>
            <span v-if="thread.is_locked" class="badge badge-dark">🔒 Locked</span>
            <span class="badge badge-primary">{{ thread.format_display }}</span>
            <span class="badge badge-secondary">{{ thread.category_display }}</span>
            <span class="badge badge-info">{{ thread.skill_display }}</span>
          </div>
          <h2>{{ thread.title }}</h2>
          <div class="text-muted">
            Started by <strong>{{ thread.author_name }}</strong>
            <span v-if="thread.author_badges && thread.author_badges.length" class="ml-1">
              <span v-for="badge in thread.author_badges" :key="badge.id"
                class="badge badge-pill badge-success mr-1" :title="badge.badge_type_display">
                ✓
              </span>
            </span>
            · {{ formatDate(thread.created_at) }}
            · 👁️ {{ thread.view_count }} views
            · 💬 {{ thread.comment_count || thread.reply_count || 0 }} comments
            · Score: {{ thread.score || 0 }}
          </div>
          <div v-if="thread.tags && thread.tags.length" class="mt-2">
            <span v-for="tag in thread.tags" :key="tag.id"
              class="badge badge-light mr-1" :style="{ borderLeft: '3px solid ' + (tag.color || '#6c757d') }">
              {{ tag.name }}
            </span>
          </div>

          <!-- Thread Locked Notice -->
          <div v-if="thread.is_locked" class="alert alert-warning mt-3 mb-0 py-2 px-3" style="font-size: 13px;">
            🔒 This thread is locked. No new replies are allowed.
          </div>

          <!-- Mod Actions -->
          <div v-if="isStaff" class="mt-3 d-flex flex-wrap" style="gap: 6px;">
            <button v-if="!thread.is_locked" class="btn btn-outline-dark btn-sm" @click="lockThread">
              🔒 Lock Thread
            </button>
            <button v-else class="btn btn-outline-success btn-sm" @click="unlockThread">
              🔓 Unlock Thread
            </button>
            <button class="btn btn-outline-danger btn-sm" @click="deleteThread">
              🗑️ Delete Thread
            </button>
          </div>
        </div>
      </div>

      <!-- Comment Sort Tabs -->
      <div class="d-flex align-items-center mb-3" style="gap: 8px;">
        <span class="text-muted small font-weight-bold">Sort comments:</span>
        <button class="btn btn-sm" :class="commentSort === 'top' ? 'btn-primary' : 'btn-outline-secondary'"
          @click="commentSort = 'top'; fetchThread()">🔝 Top</button>
        <button class="btn btn-sm" :class="commentSort === 'new' ? 'btn-primary' : 'btn-outline-secondary'"
          @click="commentSort = 'new'; fetchThread()">🕐 New</button>
      </div>

      <!-- Posts (Argument Tree) -->
      <div class="posts-section">
        <div v-for="post in rootPosts" :key="post.id" class="mb-3">
          <argument-tree-post
            :post="post"
            :depth="0"
            :max-depth="6"
            :thread-locked="thread.is_locked"
            :is-authenticated="isAuthenticated"
            :is-staff="isStaff"
            :post-types="postTypes"
            @reply="handleReply"
            @vote="handleVote"
            @report="handleReport"
            @delete-post="handleDeletePost"
          ></argument-tree-post>
        </div>
      </div>

      <!-- Root Reply Form -->
      <div v-if="!thread.is_locked && isAuthenticated" class="card mt-4">
        <div class="card-header"><strong>💬 Add to Discussion</strong></div>
        <div class="card-body">
          <div v-if="replyError" class="alert alert-danger py-2 px-3" style="font-size: 13px;">
            {{ replyError }}
          </div>
          <div class="form-group">
            <label>Post Type</label>
            <select v-model="newPost.post_type" class="form-control form-control-sm">
              <option value="opening">Opening Argument</option>
              <option value="counter">Counter-Argument</option>
              <option value="support">Supporting Point</option>
              <option value="example">Example / Evidence</option>
              <option value="framework">Framework</option>
              <option value="weighing">Weighing</option>
            </select>
          </div>
          <div class="form-group">
            <textarea v-model="newPost.content" class="form-control" rows="4"
              placeholder="Share your argument..."></textarea>
          </div>
          <button class="btn btn-primary" @click="submitPost(null)"
            :disabled="!newPost.content.trim() || submitting">
            {{ submitting ? 'Posting...' : 'Post' }}
          </button>
        </div>
      </div>

      <!-- Login prompt for anonymous users -->
      <div v-if="!isAuthenticated" class="card mt-4">
        <div class="card-body text-center py-4">
          <p class="text-muted mb-2">You must be logged in to reply.</p>
          <a href="/accounts/login/" class="btn btn-primary btn-sm">Login to Reply</a>
        </div>
      </div>

      <!-- Thread locked message (for logged-in users) -->
      <div v-if="thread.is_locked && isAuthenticated" class="card mt-4">
        <div class="card-body text-center py-4 text-muted">
          🔒 This thread is locked. No new replies are allowed.
        </div>
      </div>

      <!-- Actions Footer -->
      <div class="mt-3 d-flex flex-wrap" style="gap: 8px;">
        <button class="btn btn-sm" :class="isBookmarked ? 'btn-warning' : 'btn-outline-warning'"
          @click="toggleBookmark">
          {{ isBookmarked ? '★ Bookmarked' : '☆ Bookmark' }}
        </button>
        <a href="/forum/" class="btn btn-sm btn-outline-secondary">← Back to Forum</a>
      </div>
    </div>

    <div v-else class="alert alert-warning">Thread not found.</div>
  </div>
</template>

<script>
export default {
  name: 'ForumThreadDetail',
  data () {
    return {
      thread: null,
      loading: true,
      isBookmarked: false,
      submitting: false,
      commentSort: 'top',
      newPost: { post_type: 'opening', content: '' },
      globalError: null,
      successMsg: null,
      replyError: null,
    }
  },
  computed: {
    isAuthenticated () {
      return !!(window.threadConfig || {}).isAuthenticated
    },
    isStaff () {
      return !!(window.threadConfig || {}).isStaff
    },
    postTypes () {
      return (window.threadConfig || {}).postTypes || []
    },
    rootPosts () {
      if (!this.thread || !this.thread.posts) return []
      return this.thread.posts.filter(p => !p.parent)
    },
  },
  mounted () {
    this.fetchThread()
  },
  methods: {
    async fetchThread () {
      const config = window.threadConfig || {}
      const base = config.apiBase
      if (!base) { this.loading = false; return }
      try {
        const sep = base.includes('?') ? '&' : '?'
        const url = `${base}${sep}comment_sort=${this.commentSort}`
        const res = await fetch(url)
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error(err.detail || `HTTP ${res.status}`)
        }
        this.thread = await res.json()
      } catch (e) {
        this.globalError = `Failed to load thread: ${e.message}`
        console.error(e)
      }
      this.loading = false
    },

    async submitPost (parentId) {
      this.replyError = null
      this.submitting = true
      const csrfToken = this.getCsrf()
      const config = window.threadConfig || {}
      const body = {
        thread: this.thread.id,
        content: this.newPost.content,
        post_type: this.newPost.post_type,
      }
      if (parentId) body.parent = parentId

      try {
        const res = await fetch(config.postCreateUrl || '/forum/api/posts/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify(body),
        })
        if (res.status === 401 || res.status === 403) {
          const err = await res.json().catch(() => ({}))
          this.replyError = err.detail || 'You don\'t have permission. Please log in.'
          this.submitting = false
          return
        }
        if (res.status === 429) {
          this.replyError = 'Too many posts. Please wait before posting again.'
          this.submitting = false
          return
        }
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          const msg = typeof err === 'object' ? Object.values(err).flat().join(', ') : String(err)
          this.replyError = msg || `Error ${res.status}`
          this.submitting = false
          return
        }
        this.newPost = { post_type: 'opening', content: '' }
        this.successMsg = 'Reply posted!'
        setTimeout(() => { this.successMsg = null }, 3000)
        await this.fetchThread()
      } catch (e) {
        this.replyError = `Network error: ${e.message}`
        console.error(e)
      }
      this.submitting = false
    },

    handleReply (data) {
      this.submitReply(data)
    },
    async submitReply (data) {
      const csrfToken = this.getCsrf()
      const config = window.threadConfig || {}
      try {
        const res = await fetch(config.postCreateUrl || '/forum/api/posts/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify({
            thread: this.thread.id,
            parent: data.parent,
            content: data.content,
            post_type: data.post_type,
          }),
        })
        if (res.status === 401 || res.status === 403) {
          const err = await res.json().catch(() => ({}))
          this.globalError = err.detail || 'You don\'t have permission to reply.'
          return
        }
        if (res.status === 429) {
          this.globalError = 'Rate limited — please wait before posting again.'
          return
        }
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          const msg = typeof err === 'object' ? Object.values(err).flat().join(', ') : String(err)
          this.globalError = msg || `Failed to post reply (${res.status})`
          return
        }
        this.successMsg = 'Reply posted!'
        setTimeout(() => { this.successMsg = null }, 3000)
        await this.fetchThread()
      } catch (e) {
        this.globalError = `Network error: ${e.message}`
        console.error(e)
      }
    },

    async handleVote (data) {
      if (!this.isAuthenticated) {
        this.globalError = 'Please log in to vote.'
        return
      }
      const csrfToken = this.getCsrf()
      const config = window.threadConfig || {}
      try {
        const res = await fetch(config.voteUrl || '/forum/api/votes/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify({ post: data.post_id, vote_type: data.vote_type }),
        })
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          this.globalError = err.detail || 'Vote failed.'
          return
        }
      } catch (e) {
        this.globalError = `Vote failed: ${e.message}`
      }
      await this.fetchThread()
    },

    async handleReport (postId) {
      const reason = prompt('Report reason (spam, harassment, off_topic, misinfo, other):')
      if (!reason) return
      const csrfToken = this.getCsrf()
      const config = window.threadConfig || {}
      try {
        const res = await fetch(config.reportUrl || '/forum/api/reports/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify({ post: postId, reason: reason.trim().toLowerCase() || 'other', details: '' }),
        })
        if (res.ok) {
          this.successMsg = 'Report submitted. Thank you.'
          setTimeout(() => { this.successMsg = null }, 3000)
        } else {
          const err = await res.json().catch(() => ({}))
          this.globalError = err.detail || Object.values(err).flat().join(', ') || 'Report failed.'
        }
      } catch (e) {
        this.globalError = `Report failed: ${e.message}`
      }
    },

    async handleDeletePost (postId) {
      if (!confirm('Delete this post? This action cannot be undone.')) return
      const csrfToken = this.getCsrf()
      const config = window.threadConfig || {}
      try {
        const res = await fetch(`${config.deletePostUrlBase || '/forum/api/posts/'}${postId}/delete/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        })
        if (res.ok) {
          this.successMsg = 'Post deleted.'
          setTimeout(() => { this.successMsg = null }, 3000)
          await this.fetchThread()
        } else {
          const err = await res.json().catch(() => ({}))
          this.globalError = err.detail || 'Delete failed.'
        }
      } catch (e) {
        this.globalError = `Delete failed: ${e.message}`
      }
    },

    async lockThread () {
      if (!confirm('Lock this thread? Users will not be able to reply.')) return
      const csrfToken = this.getCsrf()
      const config = window.threadConfig || {}
      try {
        const res = await fetch(config.threadLockUrl, {
          method: 'POST',
          headers: { 'X-CSRFToken': csrfToken },
        })
        if (res.ok) {
          this.successMsg = 'Thread locked.'
          setTimeout(() => { this.successMsg = null }, 3000)
          await this.fetchThread()
        } else {
          const err = await res.json().catch(() => ({}))
          this.globalError = err.detail || 'Lock failed.'
        }
      } catch (e) { this.globalError = e.message }
    },

    async unlockThread () {
      const csrfToken = this.getCsrf()
      const config = window.threadConfig || {}
      try {
        const res = await fetch(config.threadUnlockUrl, {
          method: 'POST',
          headers: { 'X-CSRFToken': csrfToken },
        })
        if (res.ok) {
          this.successMsg = 'Thread unlocked.'
          setTimeout(() => { this.successMsg = null }, 3000)
          await this.fetchThread()
        } else {
          const err = await res.json().catch(() => ({}))
          this.globalError = err.detail || 'Unlock failed.'
        }
      } catch (e) { this.globalError = e.message }
    },

    async deleteThread () {
      if (!confirm('Delete this thread? This cannot be undone.')) return
      const csrfToken = this.getCsrf()
      const config = window.threadConfig || {}
      try {
        const res = await fetch(config.threadDeleteUrl, {
          method: 'POST',
          headers: { 'X-CSRFToken': csrfToken },
        })
        if (res.ok) {
          window.location.href = '/forum/'
        } else {
          const err = await res.json().catch(() => ({}))
          this.globalError = err.detail || 'Delete failed.'
        }
      } catch (e) { this.globalError = e.message }
    },

    async toggleBookmark () {
      const csrfToken = this.getCsrf()
      const config = window.threadConfig || {}
      const bookmarkUrl = config.bookmarkUrl || '/forum/api/bookmarks/'
      try {
        if (this.isBookmarked) {
          await fetch(`${bookmarkUrl}${this.thread.id}/`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': csrfToken },
          })
          this.isBookmarked = false
        } else {
          await fetch(bookmarkUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify({ thread: this.thread.id }),
          })
          this.isBookmarked = true
        }
      } catch (e) {
        this.globalError = `Bookmark failed: ${e.message}`
      }
    },

    formatDate (dateStr) {
      if (!dateStr) return ''
      const d = new Date(dateStr)
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
    },
    getCsrf () {
      return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
        document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1] || ''
    },
  },
}
</script>
