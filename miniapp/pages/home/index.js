const { request } = require('../../utils/request');

Page({
  data: {
    profile: {},
    loading: false
  },

  onShow() {
    this.loadProfile();
  },

  onPullDownRefresh() {
    this.loadProfile({ showLoading: false, fromPullDown: true });
  },

  async loadProfile(options = {}) {
    const { showLoading = true, fromPullDown = false } = options;
    this.setData({ loading: true });

    if (showLoading) {
      wx.showNavigationBarLoading();
    }

    try {
      const profile = await request({ url: '/mini/profile' });
      this.setData({ profile });
    } catch (_) {
      // request 已统一弹出提示
    } finally {
      this.setData({ loading: false });
      wx.hideNavigationBarLoading();
      if (fromPullDown) {
        wx.stopPullDownRefresh();
      }
    }
  },

  goScores() {
    wx.navigateTo({ url: '/pages/scores/index' });
  },

  goNotices() {
    wx.navigateTo({ url: '/pages/notices/index' });
  },

  goBehavior() {
    wx.navigateTo({ url: '/pages/behavior/index' });
  },

  logout() {
    wx.removeStorageSync('mini_token');
    wx.removeStorageSync('mini_user');
    wx.reLaunch({ url: '/pages/login/index' });
  }
});
