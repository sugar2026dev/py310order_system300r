// 使用相对路径，让Nginx代理处理
window.APP_CONFIG = {
    API_BASE_URL: '',
    DEBUG: true,
    LOG_LEVEL: 'info',
    TIMEOUTS: {
        API_REQUEST: 30000,
        OCR_PROCESSING: 60000,
        UPLOAD_FILE: 120000
    }
};

// 简单日志
window.AppLogger = {
    debug: (...args) => console.debug('[DEBUG]', ...args),
    info: (...args) => console.info('[INFO]', ...args),
    warn: (...args) => console.warn('[WARN]', ...args),
    error: (...args) => console.error('[ERROR]', ...args)
};

window.APP_ENV = 'production';

console.log('🌐 前端配置:', {
    apiBaseUrl: window.APP_CONFIG.API_BASE_URL,
    currentOrigin: window.location.origin,
    currentPath: window.location.pathname
});
