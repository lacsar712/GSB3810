const { request } = require('../../utils/request');

const DEFAULT_CANVAS_WIDTH = 690;
const DEFAULT_CANVAS_HEIGHT = 360;

Page({
  data: {
    subjects: ['全部', '语文', '数学', '英语', '物理', '化学', '生物'],
    subjectIndex: 0,
    scores: [],
    trend: [],
    loading: false,
    trendLoading: false,
    canvasWidth: DEFAULT_CANVAS_WIDTH,
    canvasHeight: DEFAULT_CANVAS_HEIGHT
  },

  onShow() {
    this.loadScores();
  },

  onReady() {
    this.syncCanvasSize();
  },

  onPullDownRefresh() {
    this.loadScores({ showLoading: false, fromPullDown: true });
  },

  onSubjectChange(e) {
    this.setData({ subjectIndex: Number(e.detail.value) }, () => {
      this.loadScores();
    });
  },

  async loadScores(options = {}) {
    const { showLoading = true, fromPullDown = false } = options;
    const subject = this.data.subjects[this.data.subjectIndex];
    this.setData({ loading: true });

    if (showLoading) {
      wx.showNavigationBarLoading();
    }

    try {
      const scores = await request({
        url: '/mini/scores',
        data: {
          subject: subject === '全部' ? undefined : subject
        }
      });
      this.setData({ scores });
      await this.loadTrend(subject);
    } catch (_) {
      this.setData({ trend: [] });
      if (subject !== '全部') {
        this.clearTrendCanvas();
      }
    } finally {
      this.setData({ loading: false });
      wx.hideNavigationBarLoading();
      if (fromPullDown) {
        wx.stopPullDownRefresh();
      }
    }
  },

  async loadTrend(subject) {
    if (subject === '全部') {
      this.setData({ trend: [], trendLoading: false });
      return;
    }

    this.setData({ trendLoading: true });
    let trend = [];
    try {
      trend = await request({
        url: '/mini/score-trend',
        data: { subject }
      });
    } catch (_) {
      trend = [];
    }

    this.setData({ trend, trendLoading: false }, () => {
      this.syncCanvasSize().then(() => {
        if (trend.length > 0) {
          this.drawTrendChart();
        } else {
          this.clearTrendCanvas();
        }
      });
    });
  },

  clearTrendCanvas() {
    const { canvasWidth, canvasHeight } = this.data;
    const ctx = wx.createCanvasContext('trendCanvas', this);
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    ctx.draw();
  },

  drawTrendChart() {
    const points = this.data.trend || [];
    const width = this.data.canvasWidth || DEFAULT_CANVAS_WIDTH;
    const height = this.data.canvasHeight || DEFAULT_CANVAS_HEIGHT;
    const scale = Math.min(width / DEFAULT_CANVAS_WIDTH, height / DEFAULT_CANVAS_HEIGHT);
    const scaleX = width / DEFAULT_CANVAS_WIDTH;
    const scaleY = height / DEFAULT_CANVAS_HEIGHT;
    const padding = {
      left: Math.round(72 * scaleX),
      right: Math.round(28 * scaleX),
      top: Math.round(24 * scaleY),
      bottom: Math.round(62 * scaleY)
    };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    const ctx = wx.createCanvasContext('trendCanvas', this);

    ctx.clearRect(0, 0, width, height);
    ctx.setFillStyle('#ffffff');
    ctx.fillRect(0, 0, width, height);

    if (!points.length) {
      ctx.setFillStyle('#8893a6');
      ctx.setFontSize(Math.max(20, Math.round(24 * scale)));
      ctx.fillText('暂无趋势数据', Math.round(width * 0.38), Math.round(height * 0.53));
      ctx.draw();
      return;
    }

    ctx.setStrokeStyle('#e7edf8');
    ctx.setLineWidth(1);
    for (let i = 0; i <= 5; i += 1) {
      const y = padding.top + (chartHeight / 5) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();
    }

    ctx.setStrokeStyle('#d0d8e8');
    ctx.setLineWidth(2);
    ctx.beginPath();
    ctx.moveTo(padding.left, padding.top);
    ctx.lineTo(padding.left, height - padding.bottom);
    ctx.lineTo(width - padding.right, height - padding.bottom);
    ctx.stroke();

    ctx.setFillStyle('#5f6e8c');
    ctx.setFontSize(Math.max(16, Math.round(20 * scale)));
    for (let i = 0; i <= 5; i += 1) {
      const scoreLabel = 100 - i * 20;
      const y = padding.top + (chartHeight / 5) * i + Math.round(6 * scaleY);
      ctx.fillText(String(scoreLabel), Math.round(18 * scaleX), y);
    }

    const stepX = points.length > 1 ? chartWidth / (points.length - 1) : 0;
    const chartPoints = points.map((item, index) => {
      const x = points.length > 1 ? padding.left + index * stepX : padding.left + chartWidth / 2;
      const y = padding.top + ((100 - Number(item.score || 0)) / 100) * chartHeight;
      return {
        x,
        y,
        dateText: String(item.exam_date || '').slice(5),
        scoreText: Number(item.score || 0).toFixed(1)
      };
    });

    ctx.setStrokeStyle('#2e8bff');
    ctx.setLineWidth(Math.max(2, Math.round(4 * scale)));
    ctx.beginPath();
    chartPoints.forEach((item, index) => {
      if (index === 0) {
        ctx.moveTo(item.x, item.y);
      } else {
        ctx.lineTo(item.x, item.y);
      }
    });
    ctx.stroke();

    chartPoints.forEach((item) => {
      ctx.setFillStyle('#ffffff');
      ctx.beginPath();
      ctx.arc(item.x, item.y, Math.max(4, Math.round(6 * scale)), 0, Math.PI * 2);
      ctx.fill();

      ctx.setStrokeStyle('#2e8bff');
      ctx.setLineWidth(Math.max(2, Math.round(3 * scale)));
      ctx.beginPath();
      ctx.arc(item.x, item.y, Math.max(4, Math.round(6 * scale)), 0, Math.PI * 2);
      ctx.stroke();

      ctx.setFillStyle('#4d5f82');
      ctx.setFontSize(Math.max(14, Math.round(18 * scale)));
      const labelX = Math.max(Math.round(8 * scaleX), item.x - Math.round(26 * scaleX));
      ctx.fillText(item.scoreText, labelX, item.y - Math.round(14 * scaleY));

      ctx.setFillStyle('#73809c');
      ctx.setFontSize(Math.max(14, Math.round(18 * scale)));
      ctx.fillText(item.dateText, Math.max(Math.round(8 * scaleX), item.x - Math.round(30 * scaleX)), height - Math.round(22 * scaleY));
    });

    ctx.draw();
  },

  syncCanvasSize() {
    return new Promise((resolve) => {
      wx.createSelectorQuery()
        .in(this)
        .select('.trend-canvas-wrap')
        .boundingClientRect((rect) => {
          if (rect && rect.width) {
            const canvasWidth = Math.floor(rect.width);
            const canvasHeight = Math.round((canvasWidth * DEFAULT_CANVAS_HEIGHT) / DEFAULT_CANVAS_WIDTH);
            this.updateCanvasSize(canvasWidth, canvasHeight, resolve);
            return;
          }

          const systemInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
          const canvasWidth = Math.floor(systemInfo.windowWidth - this.rpxToPx(104, systemInfo.windowWidth));
          const canvasHeight = Math.round((canvasWidth * DEFAULT_CANVAS_HEIGHT) / DEFAULT_CANVAS_WIDTH);
          this.updateCanvasSize(canvasWidth, canvasHeight, resolve);
        })
        .exec();
    });
  },

  updateCanvasSize(canvasWidth, canvasHeight, resolve) {
    if (this.data.canvasWidth === canvasWidth && this.data.canvasHeight === canvasHeight) {
      resolve();
      return;
    }

    this.setData({ canvasWidth, canvasHeight }, resolve);
  },

  rpxToPx(rpx, windowWidth) {
    return (rpx / 750) * windowWidth;
  }
});
