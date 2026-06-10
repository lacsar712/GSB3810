App({
  globalData: {
    token: ''
  },
  onLaunch() {
    const token = wx.getStorageSync('mini_token') || '';
    this.globalData.token = token;
  }
});
