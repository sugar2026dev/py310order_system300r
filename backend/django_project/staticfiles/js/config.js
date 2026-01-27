// ========== 环境检测 ==========
const isLocalhost = window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.hostname === '';

// ========== 环境配置 ==========
const DEVELOPMENT_CONFIG = {
    API_BASE_URL: 'http://127.0.0.1:5000',
    DEBUG: true,
    LOG_LEVEL: 'debug',
    ENABLE_PERFORMANCE_MONITORING: false,
    ENABLE_ERROR_REPORTING: false,
    TIMEOUTS: {
        API_REQUEST: 10000,
        OCR_PROCESSING: 30000,
        UPLOAD_FILE: 60000
    }
};

const PRODUCTION_CONFIG = {
    // 🔥 修复：使用与前端相同的域名和端口（通过Nginx代理）
    API_BASE_URL: window.location.origin,  // 使用当前页面的协议、域名和端口
    DEBUG: false,
    LOG_LEVEL: 'error',
    ENABLE_PERFORMANCE_MONITORING: false,
    ENABLE_ERROR_REPORTING: false,
    TIMEOUTS: {
        API_REQUEST: 30000,
        OCR_PROCESSING: 60000,
        UPLOAD_FILE: 120000
    }
};

// ========== 环境检测函数 ==========
function detectEnvironment() {
    const hostname = window.location.hostname;
    
    // 开发环境检测
    if (isLocalhost || hostname.includes('.local')) {
        return 'development';
    }
    
    // 生产环境（服务器IP）
    return 'production';
}

// ========== 选择配置 ==========
const environment = detectEnvironment();
const CONFIG = environment === 'development' ? DEVELOPMENT_CONFIG : PRODUCTION_CONFIG;

// ========== 日志系统 ==========
class Logger {
    static levels = { debug: 0, info: 1, warn: 2, error: 3, none: 4 };

    static shouldLog(level) {
        const currentLevel = this.levels[CONFIG.LOG_LEVEL] || this.levels.error;
        const targetLevel = this.levels[level] || this.levels.info;
        return targetLevel >= currentLevel;
    }

    static debug(...args) {
        if (this.shouldLog('debug') && CONFIG.DEBUG) {
            console.debug(`[DEBUG] ${new Date().toLocaleTimeString()}`, ...args);
        }
    }

    static info(...args) {
        if (this.shouldLog('info')) {
            console.info(`[INFO] ${new Date().toLocaleTimeString()}`, ...args);
        }
    }

    static warn(...args) {
        if (this.shouldLog('warn')) {
            console.warn(`[WARN] ${new Date().toLocaleTimeString()}`, ...args);
        }
    }

    static error(...args) {
        if (this.shouldLog('error')) {
            console.error(`[ERROR] ${new Date().toLocaleTimeString()}`, ...args);
        }
    }
}

// ========== 初始化 ==========
Logger.info('应用初始化', {
    environment: environment,
    apiUrl: CONFIG.API_BASE_URL,
    debugMode: CONFIG.DEBUG
});

// ========== 导出到全局 ==========
window.APP_CONFIG = CONFIG;
window.AppLogger = Logger;
window.APP_ENV = environment;
