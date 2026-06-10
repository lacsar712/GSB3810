const { request } = require('../../utils/request');

Page({
  data: {
    items: [],
    loading: false
  },

  onShow() {
    this.loadBehaviors();
  },

  onPullDownRefresh() {
    this.loadBehaviors({ showLoading: false, fromPullDown: true });
  },

  async loadBehaviors(options = {}) {
    const { showLoading = true, fromPullDown = false } = options;
    this.setData({ loading: true });

    if (showLoading) {
      wx.showNavigationBarLoading();
    }

    try {
      const items = await request({ url: '/mini/behaviors' });
      this.setData({ items });
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
