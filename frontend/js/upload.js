// ==================== 初始化 ====================
// 从全局配置获取或使用默认配置
let APP_CONFIG = window.APP_CONFIG || {
    API_BASE_URL: '',
    DEBUG: true,
    TIMEOUTS: { API_REQUEST: 30000, OCR_PROCESSING: 60000, UPLOAD_FILE: 120000 }
};

let AppLogger = window.AppLogger || {
    debug: (...args) => console.debug('[DEBUG]', ...args),
    info: (...args) => console.info('[INFO]', ...args),
    warn: (...args) => console.warn('[WARN]', ...args),
    error: (...args) => console.error('[ERROR]', ...args)
};

console.log('📤 上传模块配置:', { apiUrl: APP_CONFIG.API_BASE_URL });

// ==================== DOM元素 ====================
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadPrompt = document.getElementById('uploadPrompt');
const uploadSelected = document.getElementById('uploadSelected');
const selectedFileName = document.getElementById('selectedFileName');
const fileSize = document.getElementById('fileSize');
const fileStatus = document.getElementById('fileStatus');
const uploadProgress = document.getElementById('uploadProgress');
const progressFill = document.getElementById('progressFill');
const progressPercent = document.getElementById('progressPercent');
const uploadOcrFailed = document.getElementById('uploadOcrFailed');
const ocrFailedTitle = document.getElementById('ocrFailedTitle');
const ocrFailedMessage = document.getElementById('ocrFailedMessage');
const ocrFailedTip = document.getElementById('ocrFailedTip');
const uploadResult = document.getElementById('uploadResult');
const resultTitle = document.getElementById('resultTitle');
const resultOrderCode = document.getElementById('resultOrderCode');
const resultMessage = document.getElementById('resultMessage');
const uploadError = document.getElementById('uploadError');
const errorTitle = document.getElementById('errorTitle');
const errorOrderCode = document.getElementById('errorOrderCode');
const errorMessage = document.getElementById('errorMessage');
const previewArea = document.getElementById('previewArea');
const preview = document.getElementById('preview');
const uploadBtn = document.getElementById('uploadBtn');
const cancelBtn = document.getElementById('cancelBtn');
const nextBtn = document.getElementById('nextBtn');
const changeFileBtn = document.getElementById('changeFileBtn');
const username = document.getElementById('username');
const userType = document.getElementById('userType');
const logoutBtn = document.getElementById('logoutBtn');

// ==================== 全局变量 ====================
let selectedFile = null;
let currentUser = null;
let uploadInProgress = false;
let currentUploadAbortController = null;

// ==================== 工具函数 ====================

// 获取CSRF令牌
function getCSRFToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ==================== 界面状态管理 ====================

// 设置上传区域状态
function setUploadState(state, errorDetail = null) {
    // 重置所有显示
    uploadPrompt.style.display = 'none';
    uploadSelected.style.display = 'none';
    uploadProgress.style.display = 'none';
    uploadOcrFailed.style.display = 'none';
    uploadResult.style.display = 'none';
    uploadError.style.display = 'none';
    previewArea.style.display = 'none';

    uploadArea.className = 'upload-area';

    switch (state) {
        case 'initial':
            uploadPrompt.style.display = 'flex';
            uploadBtn.disabled = true;
            uploadBtn.innerHTML = '<i class="fas fa-upload"></i> 开始识别';
            uploadBtn.style.display = 'inline-flex';
            cancelBtn.style.display = 'none';
            nextBtn.style.display = 'none';
            AppLogger.debug('设置上传状态: 初始状态');
            break;

        case 'has-file':
            uploadArea.classList.add('has-file');
            uploadSelected.style.display = 'flex';
            previewArea.style.display = 'block';
            uploadBtn.disabled = false;
            uploadBtn.innerHTML = '<i class="fas fa-upload"></i> 开始识别';
            uploadBtn.style.display = 'inline-flex';
            cancelBtn.style.display = 'inline-flex';
            nextBtn.style.display = 'none';
            AppLogger.debug('设置上传状态: 已选择文件');
            break;

        case 'uploading':
            uploadArea.classList.add('uploading');
            uploadProgress.style.display = 'flex';
            previewArea.style.display = 'block';
            uploadBtn.disabled = true;
            uploadBtn.style.display = 'none';
            cancelBtn.style.display = 'inline-flex';
            nextBtn.style.display = 'none';
            AppLogger.debug('设置上传状态: 上传中');
            break;

        case 'ocr-failed':
            uploadArea.classList.add('ocr-failed');
            uploadOcrFailed.style.display = 'flex';
            previewArea.style.display = 'block';
            uploadBtn.disabled = false;
            uploadBtn.innerHTML = '<i class="fas fa-redo"></i> 重新识别';
            uploadBtn.style.display = 'inline-flex';
            cancelBtn.style.display = 'inline-flex';
            nextBtn.style.display = 'none';

            if (errorDetail) {
                if (ocrFailedTitle) ocrFailedTitle.textContent = errorDetail.title || '识别失败';
                if (ocrFailedMessage) ocrFailedMessage.textContent = errorDetail.message || '未识别到订单编号';
                if (ocrFailedTip) ocrFailedTip.textContent = errorDetail.tip || '请重新上传清晰的订单截图';
            }
            AppLogger.debug('设置上传状态: OCR识别失败');
            break;

        case 'success':
            uploadArea.classList.add('success');
            uploadResult.style.display = 'flex';
            previewArea.style.display = 'block';
            uploadBtn.disabled = true;
            uploadBtn.style.display = 'none';
            cancelBtn.style.display = 'none';
            nextBtn.style.display = 'inline-flex';
            AppLogger.debug('设置上传状态: 成功');
            break;

        case 'error':
            uploadArea.classList.add('error');
            uploadError.style.display = 'flex';
            previewArea.style.display = 'block';
            uploadBtn.disabled = true;
            uploadBtn.style.display = 'none';
            cancelBtn.style.display = 'none';
            nextBtn.style.display = 'inline-flex';
            AppLogger.debug('设置上传状态: 错误');
            break;
    }
}

// 更新文件状态
function updateFileStatus(text, type = 'info') {
    if (!fileStatus) return;

    fileStatus.textContent = text;

    const colors = {
        info: { bg: 'rgba(121, 187, 255, 0.2)', color: 'rgb(97, 150, 204)' },
        success: { bg: 'rgba(16, 185, 129, 0.2)', color: '#0da271' },
        warning: { bg: 'rgba(245, 158, 11, 0.2)', color: '#d97706' },
        error: { bg: 'rgba(239, 68, 68, 0.2)', color: '#dc2626' }
    };

    const color = colors[type] || colors.info;
    fileStatus.style.background = color.bg;
    fileStatus.style.color = color.color;

    AppLogger.debug('更新文件状态:', { text, type });
}

// 更新进度
function updateProgress(percent) {
    if (!progressFill || !progressPercent) return;

    progressFill.style.width = percent + '%';
    progressPercent.textContent = percent + '%';

    if (percent % 20 === 0) {
        AppLogger.debug('上传进度:', percent + '%');
    }
}

// ==================== 文件处理 ====================

// 处理文件选择
function handleFileSelect(file) {
    if (!file) return;

    if (!file.type.startsWith('image/')) {
        alert('请选择图片文件（JPG、PNG格式）');
        return;
    }

    if (file.size > 5 * 1024 * 1024) {
        alert('文件大小不能超过5MB');
        return;
    }

    selectedFile = file;

    // 显示预览
    const reader = new FileReader();
    reader.onload = (e) => {
        if (preview) preview.src = e.target.result;

        if (selectedFileName) {
            let displayName = file.name;
            if (file.name.length > 30) {
                displayName = file.name.substring(0, 15) + '...' + file.name.substring(file.name.length - 10);
            }
            selectedFileName.textContent = displayName;
        }

        if (fileSize) fileSize.textContent = formatFileSize(file.size);
        updateFileStatus('准备就绪', 'success');

        setUploadState('has-file');

        AppLogger.info('文件选择成功:', {
            name: file.name,
            size: formatFileSize(file.size),
            type: file.type
        });
    };

    reader.onerror = () => {
        AppLogger.error('文件读取失败');
        alert('文件读取失败，请重新选择');
    };

    reader.readAsDataURL(file);
}

// ==================== API 请求函数 ====================

// 通用的API请求函数
async function apiRequest(endpoint, options = {}) {
    const url = endpoint.startsWith('/') ? endpoint : '/' + endpoint;

    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken() || ''
        },
        credentials: 'include'
    };

    const finalOptions = { ...defaultOptions, ...options };

    if (options.body && options.body instanceof FormData) {
        delete finalOptions.headers['Content-Type'];
    }

    try {
        AppLogger.debug('API请求:', { url, method: finalOptions.method });
        const response = await fetch(url, finalOptions);
        const data = await response.json();
        return { success: response.ok, data: data, status: response.status };
    } catch (error) {
        AppLogger.error('API请求失败:', error);
        return { success: false, error: error.message, status: 0 };
    }
}

// 检查用户登录状态
async function checkAuth() {
    try {
        AppLogger.info('检查用户登录状态');
        const result = await apiRequest('/api/check-auth/');

        if (result.success && result.data.code === 200 && result.data.data.authenticated) {
            currentUser = result.data.data.user;

            if (currentUser && currentUser.username) {
                username.textContent = currentUser.username;
            } else {
                username.textContent = '未知用户';
                AppLogger.warn('用户数据中没有username字段:', currentUser);
            }

            userType.textContent = currentUser.is_superuser ? '超级用户' : '普通用户';

            if (currentUser.is_superuser) {
                AppLogger.warn('超级用户访问普通用户页面，跳转到管理页面');
                window.location.href = '/';
            }

            AppLogger.info('用户已登录:', currentUser.username);
            return true;
        } else {
            AppLogger.warn('用户未登录或认证失败，跳转到登录页面');
            window.location.href = '/';
            return false;
        }
    } catch (error) {
        AppLogger.error('检查登录状态失败:', error);
        username.textContent = '登录失败';
        return false;
    }
}

// 检查订单是否存在
async function checkOrderExists(orderCode) {
    try {
        AppLogger.debug('检查订单是否存在:', orderCode);
        const result = await apiRequest(`/api/orders/check/${orderCode}/`);
        return result;
    } catch (error) {
        AppLogger.error('检查订单失败:', error);
        return null;
    }
}

// ==================== 核心上传逻辑 ====================

// 保存订单到数据库
async function saveOrderToDatabase(ocrData) {
    try {
        setUploadState('uploading');
        updateProgress(90);

        AppLogger.info('开始保存订单到数据库');

        // 智能字段映射函数
        function getFieldValue(fieldNames, defaultValue = '') {
            for (const field of fieldNames) {
                if (ocrData[field] && ocrData[field].toString().trim() !== '') {
                    return ocrData[field].toString().trim();
                }
            }
            return defaultValue;
        }

        // 构建订单数据
        const orderData = {
            order_code: getFieldValue(['order_code', '订单编号']),
            upload_user: currentUser?.username || 'anonymous',
            product_name: getFieldValue(['product_name', '商品名称'], '[未识别到商品名称]'),
            specification: getFieldValue(['specification', '商品规格'], '[未识别到商品规格]'),
            product_price: getFieldValue(['product_price', '商品价格'], ''),
            payment_method: getFieldValue(['payment_method', '支付方式'], '[未识别到支付方式]'),
            actual_amount: getFieldValue(['actual_amount', '实付金额'], ''),
            logistics_company: getFieldValue(['logistics_company', '物流公司'], '[未识别到物流公司]'),
            tracking_number: getFieldValue(['tracking_number', '快递单号'], '[未识别到快递单号]'),
            order_status: getFieldValue(['order_status', '订单状态'], '待付款'),
            receiver: getFieldValue(['receiver', '收件人'], '[未识别到收件人]'),
            contact: getFieldValue(['contact', '联系方式'], '[未识别到联系方式]'),
            shipping_address: getFieldValue(['shipping_address', '收货地址'], '[未识别到收货地址]'),
            shop_name: getFieldValue(['shop_name', '店铺名称'], '[未识别到店铺名称]'),
            order_time: getFieldValue(['order_time', '下单时间'], ''),
            group_time: getFieldValue(['group_time', '拼单时间'], ''),
            ship_time: getFieldValue(['ship_time', '发货时间'], ''),
            img_path: ocrData.img_path || '',
            img_filename: ocrData.img_filename || ''
        };

        AppLogger.debug('构建的订单数据:', orderData);

        // 验证必填字段
        if (!orderData.order_code || orderData.order_code.trim() === '') {
            throw new Error('订单编号不能为空，无法保存');
        }

        // 调用 add 接口保存订单
        AppLogger.info('保存订单:', orderData.order_code);
        const result = await apiRequest('/api/orders/add/', {
            method: 'POST',
            body: JSON.stringify(orderData)
        });

        updateProgress(100);

        if (result.success && result.data.code === 200) {
            // 保存成功
            resultTitle.textContent = '识别成功';
            resultOrderCode.textContent = orderData.order_code;
            resultMessage.textContent = '订单信息已保存到系统';

            setUploadState('success');
            AppLogger.info('订单保存成功:', orderData.order_code);

        } else if (result.data && result.data.code === 409) {
            // 订单已存在
            errorTitle.textContent = '订单已存在';
            errorOrderCode.textContent = orderData.order_code;
            errorMessage.textContent = `订单已由 ${result.data?.data?.existing_uploader || '其他用户'} 上传`;
            setUploadState('error');
            AppLogger.warn('订单已存在:', orderData.order_code);

        } else {
            throw new Error(result.data?.msg || '保存失败');
        }

    } catch (error) {
        AppLogger.error('保存订单失败:', error);

        setUploadState('ocr-failed', {
            title: '保存失败',
            message: error.message,
            tip: '请稍后重试或联系管理员'
        });

        updateFileStatus('保存失败', 'error');
    }
}

// 上传图片主函数
async function uploadImage() {
    if (!selectedFile || uploadInProgress || !currentUser) {
        AppLogger.warn('上传条件不满足，无法上传');
        return;
    }

    uploadInProgress = true;
    setUploadState('uploading');
    updateProgress(10);

    try {
        const formData = new FormData();
        formData.append('image', selectedFile);

        updateProgress(30);
        AppLogger.info('开始OCR识别流程');

        // 1. 第一步：OCR识别
        updateProgress(50);
        const ocrResult = await apiRequest('/api/orders/ocr-for-form/', {
            method: 'POST',
            body: formData
        });

        updateProgress(80);

        if (ocrResult.success && ocrResult.data.code === 200) {
            const ocrData = ocrResult.data.data;
            const orderCode = ocrData.order_code;

            if (!orderCode || orderCode.trim() === '') {
                // 没有识别到订单编号
                uploadInProgress = false;

                setUploadState('ocr-failed', {
                    title: '识别失败',
                    message: '未识别到订单编号',
                    tip: '请重新上传清晰的订单截图'
                });
                updateFileStatus('未识别到订单编号', 'error');
                AppLogger.warn('OCR未识别到订单编号');

            } else {
                // 2. 第二步：检查订单是否存在
                AppLogger.info('识别到订单编号:', orderCode);

                const checkResult = await checkOrderExists(orderCode);

                if (checkResult && checkResult.success &&
                    checkResult.data.code === 200 && checkResult.data.data.exists) {
                    // 订单已存在
                    uploadInProgress = false;

                    const existingOrder = checkResult.data.data.order;
                    errorTitle.textContent = '订单已存在';
                    errorOrderCode.textContent = orderCode;
                    errorMessage.textContent = `订单已由 ${existingOrder.upload_user} 上传`;
                    setUploadState('error');
                    AppLogger.warn('订单已存在:', orderCode);

                } else {
                    // 3. 第三步：保存订单到数据库
                    await saveOrderToDatabase(ocrData);
                    uploadInProgress = false;
                }
            }

        } else if (ocrResult.data && ocrResult.data.code === 409) {
            // 订单已存在
            uploadInProgress = false;

            const orderCode = ocrResult.data?.data?.order_code || '未知';
            const uploader = ocrResult.data?.data?.existing_uploader || '其他用户';

            errorTitle.textContent = '订单已存在';
            errorOrderCode.textContent = orderCode;
            errorMessage.textContent = `订单已由 ${uploader} 上传`;
            setUploadState('error');
            AppLogger.warn('订单已存在 (响应409):', orderCode);

        } else {
            let errorMsg = ocrResult.data?.msg || 'OCR识别失败';
            uploadInProgress = false;

            setUploadState('ocr-failed', {
                title: '识别失败',
                message: errorMsg,
                tip: '请重新上传清晰的订单截图'
            });
            updateFileStatus('OCR识别失败', 'error');
            AppLogger.warn('OCR识别失败:', errorMsg);
        }

    } catch (error) {
        uploadInProgress = false;

        AppLogger.error('上传失败:', error);
        setUploadState('ocr-failed', {
            title: '上传失败',
            message: error.message,
            tip: '请检查网络连接后重试'
        });
        updateFileStatus('上传失败', 'error');
    }
}

// ==================== 取消上传功能 ====================
function cancelUpload() {
    if (currentUploadAbortController) {
        AppLogger.info('取消当前上传');
        currentUploadAbortController.abort();
        currentUploadAbortController = null;
    }

    uploadInProgress = false;
    setUploadState('initial');
    selectedFile = null;
    if (fileInput) fileInput.value = '';
    updateProgress(0);

    AppLogger.info('上传已取消');
}

// ==================== 事件监听器 ====================

function setupEventListeners() {
    // 退出登录
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            if (confirm('确定要退出登录吗？')) {
                try {
                    AppLogger.info('用户退出登录');
                    await apiRequest('/api/logout/', {
                        method: 'POST'
                    });
                    window.location.href = '/';
                } catch (error) {
                    AppLogger.error('退出失败:', error);
                    alert('退出失败，请重试');
                }
            }
        });
    }

    // 更换文件
    if (changeFileBtn) {
        changeFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            AppLogger.debug('点击更换文件按钮');
            if (fileInput) fileInput.click();
        });
    }

    // 点击上传提示区域
    if (uploadPrompt) {
        uploadPrompt.addEventListener('click', (e) => {
            e.stopPropagation();
            AppLogger.debug('点击上传提示区域');
            if (fileInput) fileInput.click();
        });
    }

    // 点击上传区域
    if (uploadArea) {
        uploadArea.addEventListener('click', (e) => {
            if (uploadInProgress) return;

            if (e.target === uploadArea && !selectedFile) {
                AppLogger.debug('点击上传区域');
                if (fileInput) fileInput.click();
            }
        });
    }

    // 拖拽事件
    if (uploadArea) {
        uploadArea.addEventListener('dragover', (e) => {
            if (!uploadInProgress) {
                e.preventDefault();
                uploadArea.classList.add('drag-over');
            }
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('drag-over');
        });

        uploadArea.addEventListener('drop', (e) => {
            if (uploadInProgress) return;

            e.preventDefault();
            uploadArea.classList.remove('drag-over');

            if (e.dataTransfer.files.length) {
                AppLogger.debug('拖拽文件到上传区域');
                handleFileSelect(e.dataTransfer.files[0]);
            }
        });
    }

    // 文件选择事件
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                AppLogger.debug('文件选择事件触发');
                handleFileSelect(e.target.files[0]);
            }
        });
    }

    // 取消按钮
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            if (uploadInProgress) {
                if (confirm('确定要取消上传吗？')) {
                    cancelUpload();
                }
            } else {
                setUploadState('initial');
                selectedFile = null;
                if (fileInput) fileInput.value = '';
                updateProgress(0);
                AppLogger.debug('取消选择文件');
            }
        });
    }

    // 继续上传按钮
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            AppLogger.debug('点击继续上传按钮');
            setUploadState('initial');
            selectedFile = null;
            if (fileInput) fileInput.value = '';
            updateProgress(0);
        });
    }

    // OCR失败状态下点击上传区域重新选择文件
    if (uploadArea) {
        uploadArea.addEventListener('click', function (e) {
            if (uploadArea.classList.contains('ocr-failed') &&
                !uploadInProgress &&
                (e.target === uploadArea ||
                    e.target.classList.contains('upload-ocr-failed') ||
                    e.target.classList.contains('ocr-failed-icon') ||
                    e.target.classList.contains('ocr-failed-content'))) {

                AppLogger.debug('OCR失败状态下点击上传区域');
                if (fileInput) fileInput.click();
            }
        });
    }

    // 开始识别按钮事件
    if (uploadBtn) {
        uploadBtn.addEventListener('click', uploadImage);
    }
}

// ==================== 页面加载 ====================

document.addEventListener('DOMContentLoaded', () => {
    AppLogger.info('DOM加载完成，开始初始化');

    // 初始化
    setUploadState('initial');

    // 检查登录状态
    checkAuth();

    // 设置事件监听器
    setupEventListeners();

    AppLogger.info('上传模块初始化完成');
});

// ==================== 全局错误处理 ====================

window.addEventListener('error', (event) => {
    AppLogger.error('全局错误:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    AppLogger.error('未处理的Promise拒绝:', event.reason);
});

// 页面卸载前的清理
window.addEventListener('beforeunload', (event) => {
    if (uploadInProgress) {
        const message = '文件正在上传，确定要离开吗？';
        event.returnValue = message;
        return message;
    }
});

// 防止浏览器后退导致重新上传
window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
        AppLogger.info('页面从缓存恢复，重置状态');
        setUploadState('initial');
        selectedFile = null;
        uploadInProgress = false;
        if (fileInput) fileInput.value = '';
        updateProgress(0);
    }
});

// 网络状态检测
window.addEventListener('online', () => {
    AppLogger.info('网络已连接');
    updateFileStatus('网络已恢复', 'success');
});

window.addEventListener('offline', () => {
    AppLogger.warn('网络已断开');
    updateFileStatus('网络连接失败', 'error');

    if (uploadInProgress) {
        cancelUpload();
        setUploadState('ocr-failed', {
            title: '网络断开',
            message: '网络连接已断开，上传已取消',
            tip: '请检查网络连接后重新上传'
        });
    }
});

AppLogger.info('upload.js 加载完成');