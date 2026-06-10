const BASE_URL = 'http://127.0.0.1:8810/api';

function request(options) {
  const token = wx.getStorageSync('mini_token') || '';
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}${options.url}`,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'content-type': 'application/json',
        Authorization: token ? `Bearer ${token}` : ''
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
          return;
        }

        let message = (res.data && res.data.message) || '请求失败';
        if (res.statusCode === 422 && res.data && Array.isArray(res.data.errors) && res.data.errors[0]?.msg) {
          message = `参数错误：${res.data.errors[0].msg}`;
        }
        wx.showToast({ title: message, icon: 'none' });

        if (res.statusCode === 401) {
          wx.removeStorageSync('mini_token');
          wx.removeStorageSync('mini_user');
          wx.reLaunch({ url: '/pages/login/index' });
        }
        reject(new Error(message));
      },
      fail: (error) => {
        wx.showToast({ title: '网络异常，请稍后重试', icon: 'none' });
        reject(error);
      }
    });
  });
}

module.exports = {
  request
};
