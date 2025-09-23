// API 工具函数
export async function apiRequest(url, options = {}) {
  const opts = {
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  };
  
  if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)) {
    opts.body = JSON.stringify(opts.body);
  }
  
  const res = await fetch(url, opts);
  const data = await res.json().catch(() => ({ error: 'Invalid JSON' }));
  
  if (!res.ok) {
    const err = new Error(data.detail || data.message || `HTTP ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  
  return data;
}

export async function apiGet(url) {
  return apiRequest(url, { method: 'GET' });
}

export async function apiPost(url, body) {
  return apiRequest(url, { method: 'POST', body });
}

export async function apiPut(url, body) {
  return apiRequest(url, { method: 'PUT', body });
}

export async function apiDelete(url) {
  return apiRequest(url, { method: 'DELETE' });
}

// 登出函数
export function logout() {
  if (confirm('确定要退出登录吗？')) {
    fetch('/api/logout', { method: 'POST' })
      .then(() => window.location.href = '/login')
      .catch(() => window.location.href = '/login');
  }
}

// 通知系统
export function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.classList.add('show');
  }, 10);
  
  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// 表单验证
export function validateForm(formData, rules) {
  const errors = {};
  
  for (const [field, rule] of Object.entries(rules)) {
    const value = formData[field];
    
    if (rule.required && !value) {
      errors[field] = rule.message || `${field} 不能为空`;
      continue;
    }
    
    if (rule.pattern && value && !rule.pattern.test(value)) {
      errors[field] = rule.message || `${field} 格式不正确`;
    }
    
    if (rule.minLength && value && value.length < rule.minLength) {
      errors[field] = rule.message || `${field} 至少需要 ${rule.minLength} 个字符`;
    }
    
    if (rule.maxLength && value && value.length > rule.maxLength) {
      errors[field] = rule.message || `${field} 不能超过 ${rule.maxLength} 个字符`;
    }
  }
  
  return Object.keys(errors).length > 0 ? errors : null;
}

// 工具函数
export function formatDate(dateString) {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN');
}

export function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function truncateString(str, maxLength = 50) {
  if (!str) return '';
  return str.length > maxLength ? str.substring(0, maxLength) + '...' : str;
}

export function copyToClipboard(text) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => {
      showNotification('已复制到剪贴板', 'success');
    }).catch(() => {
      showNotification('复制失败', 'error');
    });
  } else {
    // 降级方案
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    showNotification('已复制到剪贴板', 'success');
  }
}

// 防抖函数
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// 节流函数
export function throttle(func, limit) {
  let inThrottle;
  return function() {
    const args = arguments;
    const context = this;
    if (!inThrottle) {
      func.apply(context, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  }
}

// 添加通知样式
const style = document.createElement('style');
style.textContent = `
  .notification {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 12px 16px;
    border-radius: 8px;
    color: white;
    font-size: 14px;
    z-index: 1000;
    transform: translateX(100%);
    transition: transform 0.3s ease;
    max-width: 300px;
  }
  
  .notification.show {
    transform: translateX(0);
  }
  
  .notification-info {
    background: var(--brand, #3b82f6);
  }
  
  .notification-success {
    background: var(--ok, #22c55e);
  }
  
  .notification-warning {
    background: var(--warn, #f59e0b);
  }
  
  .notification-error {
    background: var(--danger, #ef4444);
  }
`;
document.head.appendChild(style);
