const { request } = require('../../utils/request');

Page({
  data: {
    roleOptions: ['学生', '家长'],
    roleIndex: 0,
    loading: false,
    form: {
      code: '',
      student_no: ''
    }
  },

  onRoleChange(e) {
    this.setData({ roleIndex: Number(e.detail.value) });
  },

  onCodeInput(e) {
    this.setData({ 'form.code': e.detail.value });
  },

  onStudentNoInput(e) {
    this.setData({ 'form.student_no': e.detail.value });
  },

  async handleLogin() {
    const code = this.data.form.code.trim();
    const studentNo = this.data.form.student_no.trim();
    if (!code || !studentNo) {
      wx.showToast({ title: '授权码和学号均不能为空', icon: 'none' });
      return;
    }

    this.setData({ loading: true });
    const role = this.data.roleIndex === 0 ? 'STUDENT' : 'PARENT';

    try {
      const data = await request({
        url: '/auth/wechat-login',
        method: 'POST',
        data: {
          code,
          role,
          student_no: studentNo
        }
      });

      wx.setStorageSync('mini_token', data.access_token);
      wx.setStorageSync('mini_user', data.user);
      wx.reLaunch({ url: '/pages/home/index' });
    } catch (_) {
      // request 已统一弹出提示
    } finally {
      this.setData({ loading: false });
    }
  }
});
