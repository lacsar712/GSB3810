const { request } = require('../../utils/request');

Page({
  data: {
    notices: [],
    loading: false
  },

  onShow() {
    this.loadNotices();
  },

  onPullDownRefresh() {
    this.loadNotices({ showLoading: false, fromPullDown: true });
  },

  async loadNotices(options = {}) {
    const { showLoading = true, fromPullDown = false } = options;
    this.setData({ loading: true });

    if (showLoading) {
      wx.showNavigationBarLoading();
    }

    try {
      const notices = await request({ url: '/mini/notices' });
      this.setData({ notices });
    } catch (_) {
      // request 已统一弹出提示
    } finally {
      this.setData({ loading: false });
      wx.hideNavigationBarLoading();
      if (fromPullDown) {
        wx.stopPullDownRefresh();
      }
    }
  }
});
