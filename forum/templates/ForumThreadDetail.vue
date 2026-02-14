<template>
  <div class="forum-thread-detail">
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
    </div>

    <div v-else-if="thread">
      <!-- Thread Header -->
      <div class="card mb-4">
        <div class="card-body">
          <div class="d-flex flex-wrap mb-2">
            <span v-if="thread.is_pinned" class="badge badge-warning mr-2">📌 Pinned</span>
            <span v-if="thread.is_locked" class="badge badge-dark mr-2">🔒 Locked</span>
            <span class="badge badge-primary mr-2">{{ thread.format_display }}</span>
            <span class="badge badge-secondary mr-2">{{ thread.category_display }}</span>
            <span class="badge badge-info mr-2">{{ thread.skill_display }}</span>
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
          </div>
          <div v-if="thread.tags && thread.tags.length" class="mt-2">
            <span v-for="tag in thread.tags" :key="tag.id"
              class="badge badge-light mr-1" :style="{ borderLeft: '3px solid ' + (tag.color || '#6c757d') }">
              {{ tag.name }}
            </span>
          </div>
        </div>
      </div>

      <!-- Posts (Argument Tree) -->
      <div class="posts-section">
        <div v-for="post in rootPosts" :key="post.id" class="mb-3">
          <argument-tree-post
            :post="post"
            :thread-locked="thread.is_locked"
            @reply="handleReply"
            @vote="handleVote"
          ></argument-tree-post>
        </div>
      </div>

      <!-- Reply Form (for root-level posts) -->
      <div v-if="!thread.is_locked" class="card mt-4">
        <div class="card-header"><strong>💬 Add to Discussion</strong></div>
        <div class="card-body">
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
            :disabled="!newPost.content.trim()">Post</button>
        </div>
      </div>

      <!-- Bookmarks -->
      <div class="mt-3">
        <button class="btn btn-sm" :class="isBookmarked ? 'btn-warning' : 'btn-outline-warning'"
          @click="toggleBookmark">
          {{ isBookmarked ? '★ Bookmarked' : '☆ Bookmark' }}
        </button>
        <a href="/forum/" class="btn btn-sm btn-outline-secondary ml-2">← Back to Forum</a>
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
      newPost: { post_type: 'opening', content: '' },
    }
  },
  computed: {
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
      const url = config.apiBase
      if (!url) { this.loading = false; return }
      try {
        const res = await fetch(url)
        if (!res.ok) throw new Error('Not found')
        this.thread = await res.json()
      } catch (e) { console.error(e) }
      this.loading = false
    },
    async submitPost (parentId) {
      const csrfToken = this.getCsrf()
      const body = {
        thread: this.thread.id,
        content: this.newPost.content,
        post_type: this.newPost.post_type,
      }
      if (parentId) body.parent = parentId

      const config = window.threadConfig || {}
      try {
        const res = await fetch(config.postCreateUrl || '/forum/api/posts/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify(body),
        })
        if (res.ok) {
          this.newPost = { post_type: 'opening', content: '' }
          this.fetchThread()
        }
      } catch (e) { console.error(e) }
    },
    handleReply (data) {
      // data = { parentId, content, post_type }
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
            parent: data.parentId,
            content: data.content,
            post_type: data.post_type,
          }),
        })
        if (res.ok) this.fetchThread()
      } catch (e) { console.error(e) }
    },
    async handleVote (data) {
      const csrfToken = this.getCsrf()
      const config = window.threadConfig || {}
      await fetch(config.voteUrl || '/forum/api/votes/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({ post: data.postId, vote_type: data.voteType }),
      })
      this.fetchThread()
    },
    async toggleBookmark () {
      const csrfToken = this.getCsrf()
      const config = window.threadConfig || {}
      const bookmarkUrl = config.bookmarkUrl || '/forum/api/bookmarks/'
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
