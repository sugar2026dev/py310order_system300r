// ==================== 初始化 ====================
// 检查配置是否加载
let API_BASE_URL, AppLogger, APP_CONFIG;

if (window.APP_CONFIG && window.AppLogger) {
  API_BASE_URL = window.APP_CONFIG.API_BASE_URL;
  AppLogger = window.AppLogger;  // 使用 AppLogger 避免冲突
  APP_CONFIG = window.APP_CONFIG;
} else {
  console.warn('使用后备配置');
  // 后备配置
  const isLocalDev = window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1';

  API_BASE_URL = isLocalDev ? 'http://127.0.0.1:8000' : 'http://101.201.31.24:8000';

  AppLogger = {  // 改为 AppLogger
    debug: (...args) => console.debug('[DEBUG]', ...args),
    info: (...args) => console.info('[INFO]', ...args),
    warn: (...args) => console.warn('[WARN]', ...args),
    error: (...args) => console.error('[ERROR]', ...args)
  };

  APP_CONFIG = {
    API_BASE_URL: API_BASE_URL,
    DEBUG: true,
    TIMEOUTS: {
      API_REQUEST: 10000,
      OCR_PROCESSING: 30000,
      UPLOAD_FILE: 60000
    }
  };
}

AppLogger.info('应用配置加载完成', { API_BASE_URL });

// 创建 Vue 应用
const { createApp, ref, reactive, computed, onMounted } = Vue;
const { ElMessage, ElMessageBox, ElLoading } = ElementPlus;

// ==================== CSRF Token 配置 ====================
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

// 配置 axios
axios.defaults.xsrfCookieName = 'csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';
axios.defaults.withCredentials = true;
axios.defaults.timeout = APP_CONFIG.TIMEOUTS ? APP_CONFIG.TIMEOUTS.API_REQUEST : 10000;

// 请求拦截器
axios.interceptors.request.use(
  (config) => {
    if (['post', 'put', 'delete', 'patch'].includes(config.method.toLowerCase())) {
      const token = getCSRFToken();
      if (token) {
        config.headers['X-CSRFToken'] = token;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      switch (error.response.status) {
        case 403:
          AppLogger.error('CSRF验证失败或权限不足');
          ElMessage.error('会话已过期，请刷新页面');
          setTimeout(() => window.location.reload(), 1500);
          break;
        case 404:
          AppLogger.warn('请求的资源不存在');
          break;
        case 500:
          AppLogger.error('服务器内部错误');
          ElMessage.error('服务器错误，请稍后重试');
          break;
        case 502:
        case 503:
        case 504:
          AppLogger.error('服务器不可用');
          ElMessage.error('服务器暂时不可用，请稍后重试');
          break;
        default:
          AppLogger.error(`请求错误: ${error.response.status}`);
      }
    } else if (error.code === 'ECONNABORTED') {
      AppLogger.error('请求超时');
      ElMessage.error('请求超时，请检查网络连接');
    } else if (error.message.includes('Network Error')) {
      AppLogger.error('网络连接失败');
      ElMessage.error('网络连接失败，请检查网络设置');
    }
    return Promise.reject(error);
  }
);

// ==================== 创建应用实例 ====================
const app = createApp({
  setup() {
    // 状态管理
    const isLoginSuccess = ref(false);
    const isRegisterMode = ref(false);
    const currentUser = reactive({
      username: '',
      user_type: 0,
      user_type_name: ''
    });

    // 移动端状态
    const mobileMenuOpen = ref(false);

    // 登录表单
    const loginForm = reactive({
      username: '',
      password: '',
      remember: false
    });

    const loginErrors = reactive({
      username: '',
      password: ''
    });

    // 注册表单
    const registerForm = reactive({
      username: '',
      password: '',
      checkPassword: ''
    });

    const registerErrors = reactive({
      username: '',
      password: '',
      checkPassword: ''
    });

    // 订单管理
    const orders = ref([]);
    const pageOrders = ref([]);
    const searchKeyword = ref('');
    const selectedOrders = ref([]);
    const currentPage = ref(1);
    const pageSize = ref(10);
    const total = ref(0);
    const dateRange = ref([]);
    const activeIndex = ref('1');

    // 对话框状态
    const dialogVisible = ref(false);
    const isView = ref(false);
    const isEdit = ref(false);
    const dialogTitle = ref('');
    const isUploading = ref(false);
    const ocrResult = ref(null);
    const ocrStatus = ref(null);
    const originalOrderData = reactive({});
    const imageLoadError = ref(false);
    const exportLoading = ref(false);
    const imageLoaded = ref(false);

    // 订单表单
    const orderForm = reactive({
      id: null,
      order_code: '',
      upload_user: '',
      product_name: '',
      specification: '',
      product_price: '',
      payment_method: '',
      actual_amount: '',
      logistics_company: '',
      tracking_number: '',
      order_status: '',
      receiver: '',
      contact: '',
      shipping_address: '',
      shop_name: '',
      order_time: '',
      group_time: '',
      ship_time: '',
      create_time: '',
      update_time: '',
      img_path: '',
      img_filename: ''
    });

    // ==================== 验证方法 ====================
    const validateLoginForm = () => {
      let isValid = true;
      loginErrors.username = '';
      loginErrors.password = '';

      if (!loginForm.username.trim()) {
        loginErrors.username = '请输入用户名';
        isValid = false;
      }

      if (!loginForm.password) {
        loginErrors.password = '请输入密码';
        isValid = false;
      }

      return isValid;
    };

    const validateRegisterForm = () => {
      let isValid = true;
      registerErrors.username = '';
      registerErrors.password = '';
      registerErrors.checkPassword = '';

      const username = registerForm.username.trim();
      if (!username) {
        registerErrors.username = '请输入用户名';
        isValid = false;
      } else if (username.length < 3) {
        registerErrors.username = '用户名至少需要3个字符';
        isValid = false;
      } else if (username.length > 9) {
        registerErrors.username = '用户名不能超过9个字符';
        isValid = false;
      } else if (!/^[a-zA-Z0-9_]+$/.test(username)) {
        registerErrors.username = '用户名只能包含字母、数字和下划线';
        isValid = false;
      }

      if (!registerForm.password) {
        registerErrors.password = '请输入密码';
        isValid = false;
      } else if (registerForm.password.length < 6) {
        registerErrors.password = '密码长度至少6位';
        isValid = false;
      }

      if (!registerForm.checkPassword) {
        registerErrors.checkPassword = '请确认密码';
        isValid = false;
      } else if (registerForm.checkPassword !== registerForm.password) {
        registerErrors.checkPassword = '两次输入密码不一致';
        isValid = false;
      }

      return isValid;
    };

    // ==================== 移动端适配方法 ====================
    const toggleMobileMenu = () => {
      mobileMenuOpen.value = !mobileMenuOpen.value;
      const sidebar = document.querySelector('.main-sidebar');
      if (sidebar) {
        if (mobileMenuOpen.value) {
          sidebar.classList.add('active');
          // 点击外部关闭菜单
          document.addEventListener('click', closeMobileMenuOutside);
        } else {
          sidebar.classList.remove('active');
          document.removeEventListener('click', closeMobileMenuOutside);
        }
      }
    };

    const closeMobileMenuOutside = (event) => {
      const sidebar = document.querySelector('.main-sidebar');
      const toggleBtn = document.querySelector('.mobile-menu-toggle');

      if (sidebar && !sidebar.contains(event.target) &&
        toggleBtn && !toggleBtn.contains(event.target)) {
        mobileMenuOpen.value = false;
        sidebar.classList.remove('active');
        document.removeEventListener('click', closeMobileMenuOutside);
      }
    };

    const handleMobileMenuItemClick = () => {
      if (mobileMenuOpen.value) {
        mobileMenuOpen.value = false;
        const sidebar = document.querySelector('.main-sidebar');
        if (sidebar) {
          sidebar.classList.remove('active');
        }
        document.removeEventListener('click', closeMobileMenuOutside);
      }
    };

    const handleResize = () => {
      if (window.innerWidth > 768 && mobileMenuOpen.value) {
        mobileMenuOpen.value = false;
        const sidebar = document.querySelector('.main-sidebar');
        if (sidebar) {
          sidebar.classList.remove('active');
        }
        document.removeEventListener('click', closeMobileMenuOutside);
      }
    };

    // 显示移动端提示
    const showMobileTips = () => {
      if (window.innerWidth <= 768) {
        const hasSeenTips = localStorage.getItem('mobileTipsShown');
        if (!hasSeenTips && isLoginSuccess.value) {
          setTimeout(() => {
            ElMessage({
              message: '💡 提示：左右滑动表格查看更多列，点击左上角菜单展开侧边栏',
              type: 'info',
              duration: 5000,
              showClose: true
            });
            localStorage.setItem('mobileTipsShown', 'true');
          }, 2000);
        }
      }
    };

    // ==================== 登录/注册方法 ====================
    const submitLogin = async () => {
      if (!validateLoginForm()) return;

      try {
        AppLogger.info('用户登录尝试:', loginForm.username);
        const response = await axios.post(`${API_BASE_URL}/api/login/`, {
          username: loginForm.username,
          password: loginForm.password,
          remember: loginForm.remember
        });

        if (response.data.code === 200) {
          const userData = response.data.data;
          AppLogger.info('登录成功:', userData.username);

          currentUser.username = userData.username;
          currentUser.is_superuser = userData.is_superuser;
          currentUser.user_type_name = userData.is_superuser ? '超级用户' : '普通用户';

          if (loginForm.remember) {
            localStorage.setItem('rememberedUser', loginForm.username);
          } else {
            localStorage.removeItem('rememberedUser');
          }

          // 使用 is_superuser 判断
          if (userData.is_superuser) {
            isLoginSuccess.value = true;
            await loadOrders();
            showMobileTips(); // 显示移动端提示
          } else {
            window.location.href = '/upload.html';
          }
        } else {
          AppLogger.warn('登录失败:', response.data.msg);
          loginForm.password = '';
          loginErrors.password = '用户名或密码错误';
        }
      } catch (error) {
        AppLogger.error('登录请求失败:', error);
        loginForm.password = '';
        loginErrors.password = '登录失败，请检查网络连接';
      }
    };

    const submitRegister = async () => {
      if (!validateRegisterForm()) return;

      try {
        const loading = ElLoading.service({
          lock: true,
          text: '注册中...',
          background: 'rgba(0, 0, 0, 0.7)'
        });

        AppLogger.info('用户注册尝试:', registerForm.username);
        const response = await axios.post(`${API_BASE_URL}/api/register/`, {
          username: registerForm.username,
          password: registerForm.password
        });

        loading.close();

        if (response.data.code === 200) {
          AppLogger.info('注册成功:', registerForm.username);
          ElMessage.success('注册成功！');
          loginForm.username = registerForm.username;
          loginForm.password = '';
          isRegisterMode.value = false;
          registerForm.username = '';
          registerForm.password = '';
          registerForm.checkPassword = '';
        } else {
          AppLogger.warn('注册失败:', response.data.msg);
          ElMessage.error(response.data.msg || '注册失败');
        }
      } catch (error) {
        AppLogger.error('注册请求失败:', error);
        ElMessage.error('注册失败，请重试');
      }
    };

    const logout = async () => {
      try {
        await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
          type: 'warning'
        });

        AppLogger.info('用户退出登录:', currentUser.username);
        await axios.post(`${API_BASE_URL}/api/logout/`);

        // 清空用户数据
        loginForm.username = '';
        loginForm.password = '';
        loginForm.remember = false;
        registerForm.username = '';
        registerForm.password = '';
        registerForm.checkPassword = '';

        Object.keys(loginErrors).forEach(key => loginErrors[key] = '');
        Object.keys(registerErrors).forEach(key => registerErrors[key] = '');
        localStorage.removeItem('rememberedUser');
        isLoginSuccess.value = false;

        currentUser.username = '';
        currentUser.user_type = 0;
        currentUser.user_type_name = '';

        ElMessage.success('已安全退出登录');
        AppLogger.info('退出登录成功');

      } catch (error) {
        if (error !== 'cancel') {
          AppLogger.error('退出登录失败:', error);
          ElMessage.error('退出失败');
        }
      }
    };

    const showForgotPassword = () => {
      ElMessage.info('请联系管理员重置密码');
    };

    // ==================== 日期格式化 ====================
    const formatDate = (date) => {
      if (!date) return '';
      if (typeof date === 'string') {
        const match = date.match(/^(\d{4}-\d{2}-\d{2})/);
        return match ? match[1] : date;
      }
      if (date instanceof Date || (date && date.getDate)) {
        try {
          const year = date.getFullYear();
          const month = String(date.getMonth() + 1).padStart(2, '0');
          const day = String(date.getDate()).padStart(2, '0');
          return `${year}-${month}-${day}`;
        } catch (e) {
          return '';
        }
      }
      return '';
    };

    const formatDateForExport = (date) => {
      return formatDate(date);
    };

    // ==================== 搜索功能 ====================
    const handleSearch = () => {
      currentPage.value = 1;
      loadOrders();
    };

    const handleDateChange = () => {
      if (window.dateChangeTimeout) {
        clearTimeout(window.dateChangeTimeout);
      }
      window.dateChangeTimeout = setTimeout(() => {
        handleSearch();
      }, 300);
    };

    const handleClearSearch = () => {
      searchKeyword.value = '';
      handleSearch();
    };

    const searchOrders = () => {
      handleSearch();
    };

    const getAllOrders = () => {
      searchKeyword.value = '';
      dateRange.value = [];
      currentPage.value = 1;
      loadOrders();
    };

    // ==================== 订单管理方法 ====================
    const loadOrders = async () => {
      const loading = ElLoading.service({
        lock: true,
        text: '加载中...',
        background: 'rgba(0, 0, 0, 0.7)'
      });

      try {
        const params = {
          page: currentPage.value,
          page_size: pageSize.value,
          keyword: searchKeyword.value
        };

        if (dateRange.value && dateRange.value.length === 2) {
          const [startDate, endDate] = dateRange.value;
          const formattedStart = formatDate(startDate);
          const formattedEnd = formatDate(endDate);

          if (formattedStart && formattedEnd) {
            params.start_date = formattedStart;
            params.end_date = formattedEnd;
          }
        }

        AppLogger.debug('加载订单参数:', params);
        const response = await axios.get(`${API_BASE_URL}/api/orders/`, {
          params: params
        });

        if (response.data.code === 200) {
          orders.value = response.data.data.orders;
          total.value = orders.value.length;
          getPageOrders();
          AppLogger.info('订单加载成功，数量:', total.value);
        } else {
          AppLogger.error('加载订单失败:', response.data);
          ElMessage.error('加载订单失败');
        }
      } catch (error) {
        AppLogger.error('加载订单请求失败:', error);
        ElMessage.error('加载订单失败');
      } finally {
        loading.close();
      }
    };

    const getPageOrders = () => {
      pageOrders.value = [];
      const start = (currentPage.value - 1) * pageSize.value;
      const end = Math.min(start + pageSize.value, total.value);

      for (let i = start; i < end; i++) {
        if (orders.value[i]) {
          pageOrders.value.push(orders.value[i]);
        }
      }
    };

    const handleSelectionChange = (rows) => {
      selectedOrders.value = rows.map(row => row.id);
    };

    // ==================== 导出功能 ====================
    const exportToExcel = async () => {
      try {
        exportLoading.value = true;
        ElMessage.info('正在准备导出数据...');

        const params = new URLSearchParams();
        if (searchKeyword.value) {
          params.append('keyword', searchKeyword.value);
        }

        if (dateRange.value && dateRange.value.length === 2) {
          const [start, end] = dateRange.value;
          params.append('start_date', formatDateForExport(start));
          params.append('end_date', formatDateForExport(end));
        }

        if (total.value > 1000) {
          const confirmed = await ElMessageBox.confirm(
            `当前筛选结果有 ${total.value} 条数据，导出可能需要较长时间。是否继续？`,
            '提示',
            {
              type: 'warning',
              confirmButtonText: '继续导出',
              cancelButtonText: '取消'
            }
          );

          if (!confirmed) {
            exportLoading.value = false;
            return;
          }
        }

        AppLogger.info('开始导出Excel数据');
        const response = await axios.get(`${API_BASE_URL}/api/orders/export/?${params}`, {
          responseType: 'blob',
          timeout: 60000
        });

        const contentDisposition = response.headers['content-disposition'];
        let filename = '订单数据.xlsx';

        if (contentDisposition) {
          const match = contentDisposition.match(/filename="(.+)"/);
          if (match) {
            filename = decodeURIComponent(match[1]);
          }
        }

        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        ElMessage.success(`导出成功！文件 "${filename}" 已开始下载`);
        AppLogger.info('Excel导出成功:', filename);

      } catch (error) {
        AppLogger.error('导出Excel失败:', error);
        ElMessage.error('导出失败，请重试');
      } finally {
        exportLoading.value = false;
      }
    };

    // ==================== 图片处理 ====================
    const handleImageLoad = (event) => {
      imageLoaded.value = true;
      imageLoadError.value = false;
      const imgElement = event.target;
      imgElement.style.transition = 'opacity 0.5s ease';
      imgElement.style.opacity = '1';
    };

    const handleImageError = (event) => {
      imageLoadError.value = true;
      imageLoaded.value = false;
      const imgElement = event.target;

      if (isView.value || isEdit.value) {
        imgElement.style.display = 'none';
        if (!imgElement.parentNode.querySelector('.image-error-placeholder')) {
          const errorDiv = document.createElement('div');
          errorDiv.className = 'image-error-placeholder';
          errorDiv.innerHTML = `
            <i class="fas fa-image" style="font-size: 48px; color: #ccc; margin-bottom: 10px;"></i>
            <div style="color: #999; font-size: 14px;">订单图片无法加载</div>
          `;
          errorDiv.style.cssText = `
            width: 100%; height: 100%; display: flex; flex-direction: column;
            align-items: center; justify-content: center; background: #f8fafc;
            border-radius: 8px; border: 1px dashed #e4e7ed; text-align: center;
            padding: 20px; box-sizing: border-box;
          `;
          imgElement.parentNode.appendChild(errorDiv);
        }
      }
    };

    const buildImageUrl = (order) => {
      imageLoadError.value = false;
      imageLoaded.value = false;

      const possibleUrls = [];
      if (order.img_url && order.img_url.trim() !== '') {
        let url = order.img_url;
        if (!url.startsWith('http') && !url.startsWith('blob:')) {
          url = url.startsWith('/') ? `${API_BASE_URL}${url}` : `${API_BASE_URL}/${url}`;
        }
        possibleUrls.push({ url, source: 'img_url', priority: 1 });
      }

      if (order.img_path && order.img_path.trim() !== '') {
        let url = order.img_path;
        if (!url.startsWith('http') && !url.startsWith('blob:')) {
          url = url.startsWith('/') ? `${API_BASE_URL}${url}` : `${API_BASE_URL}/${url}`;
        }
        possibleUrls.push({ url, source: 'img_path', priority: 2 });
      }

      if (order.img_filename && order.img_filename.trim() !== '') {
        const filename = order.img_filename;
        const directories = ['/media/order_images/', '/media/temp/', '/uploads/', '/static/order_images/'];
        directories.forEach(dir => {
          possibleUrls.push({ url: `${API_BASE_URL}${dir}${filename}`, source: `img_filename + ${dir}`, priority: 3 });
        });
      }

      if (possibleUrls.length > 0) {
        possibleUrls.sort((a, b) => a.priority - b.priority);
        const initialUrl = possibleUrls[0].url;
        orderForm.img_path = initialUrl;
        orderForm.img_filename = order.img_filename || initialUrl.split('/').pop() || '';
        return initialUrl;
      }

      orderForm.img_path = '';
      orderForm.img_filename = '';
      return null;
    };

    // ==================== 对话框方法 ====================
    const showAddDialog = () => {
      resetForm();
      isView.value = false;
      isEdit.value = false;
      dialogTitle.value = '添加订单';
      orderForm.upload_user = currentUser.username;
      orderForm.order_status = '';
      ocrResult.value = null;
      ocrStatus.value = null;
      imageLoadError.value = false;
      imageLoaded.value = false;
      isUploading.value = false;
      Object.keys(originalOrderData).forEach(key => delete originalOrderData[key]);
      dialogVisible.value = true;
      AppLogger.debug('打开添加订单对话框');
    };

    const viewOrder = async (order) => {
      resetForm();
      Object.assign(orderForm, order);
      buildImageUrl(order);
      isView.value = true;
      isEdit.value = false;
      dialogTitle.value = '查看订单';
      ocrResult.value = null;
      ocrStatus.value = null;
      dialogVisible.value = true;
      AppLogger.debug('查看订单:', order.order_code);
    };

    const editOrder = async (order) => {
      resetForm();
      Object.assign(orderForm, order);
      buildImageUrl(order);
      Object.keys(orderForm).forEach(key => originalOrderData[key] = orderForm[key]);
      isView.value = false;
      isEdit.value = true;
      dialogTitle.value = '编辑订单';
      ocrResult.value = null;
      ocrStatus.value = null;
      dialogVisible.value = true;
      AppLogger.debug('编辑订单:', order.order_code);
    };

    const deleteOrder = async (order) => {
      try {
        await ElMessageBox.confirm(`确定要删除订单 "${order.order_code}" 吗？`, '提示', {
          type: 'warning'
        });

        AppLogger.info('开始删除订单:', order.order_code);
        const response = await axios.post(`${API_BASE_URL}/api/orders/batch-delete/`, {
          order_ids: [order.id]
        });

        if (response.data.code === 200) {
          await loadOrders();
          ElMessage.success('删除成功');
          AppLogger.info('删除订单成功:', order.order_code);
        } else {
          AppLogger.error('删除订单失败:', response.data);
          ElMessage.error(response.data.msg || '删除失败');
        }
      } catch (error) {
        if (error !== 'cancel') {
          AppLogger.error('删除订单异常:', error);
          if (error.response?.status === 403) {
            ElMessage.error('会话已过期，请刷新页面后重试');
            setTimeout(() => window.location.reload(), 1500);
          } else {
            ElMessage.error('删除失败，请重试');
          }
        }
      }
    };

    const batchDelete = async () => {
      if (selectedOrders.value.length === 0) {
        ElMessage.warning('请选择要删除的订单');
        return;
      }

      try {
        await ElMessageBox.confirm(`确定要删除选中的 ${selectedOrders.value.length} 个订单吗？`, '提示', {
          type: 'warning'
        });

        AppLogger.info('批量删除订单，数量:', selectedOrders.value.length);
        const response = await axios.post(`${API_BASE_URL}/api/orders/batch-delete/`, {
          order_ids: selectedOrders.value
        });

        if (response.data.code === 200) {
          await loadOrders();
          selectedOrders.value = [];
          ElMessage.success('批量删除成功');
          AppLogger.info('批量删除成功');
        } else {
          AppLogger.error('批量删除失败:', response.data);
          ElMessage.error(response.data.msg || '批量删除失败');
        }
      } catch (error) {
        if (error !== 'cancel') {
          AppLogger.error('批量删除异常:', error);
          ElMessage.error('批量删除失败');
        }
      }
    };

    const closeDialogForm = () => {
      if (orderForm.img_path && orderForm.img_path.startsWith('blob:')) {
        try {
          URL.revokeObjectURL(orderForm.img_path);
        } catch (e) { }
      }
      resetForm();
      dialogVisible.value = false;
      isView.value = false;
      isEdit.value = false;
      isUploading.value = false;
      ocrResult.value = null;
      ocrStatus.value = null;
      imageLoadError.value = false;
      imageLoaded.value = false;
    };

    const resetForm = () => {
      Object.keys(orderForm).forEach(key => orderForm[key] = '');
      orderForm.upload_user = currentUser.username;
      orderForm.order_status = '';
    };

    // ==================== 图片上传和OCR ====================
    const beforeImageUpload = (file) => {
      if (isView.value || isEdit.value) {
        ElMessage.warning('当前模式下不允许上传图片');
        return false;
      }

      const isImage = file.type.startsWith('image/');
      const isLt5M = file.size / 1024 / 1024 < 5;
      const supportedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];

      if (!isImage || !supportedTypes.includes(file.type)) {
        ElMessage.error('只能上传JPG、PNG、GIF格式的图片!');
        return false;
      }
      if (!isLt5M) {
        ElMessage.error('图片大小不能超过5MB!');
        return false;
      }

      return true;
    };

    const showOCRResult = (type, title, message, hint = '') => {
      const statusMap = {
        success: { type: 'success', icon: 'fas fa-check-circle', title, message, hint },
        error: { type: 'error', icon: 'fas fa-exclamation-circle', title, message, hint },
        warning: { type: 'warning', icon: 'fas fa-exclamation-triangle', title, message, hint },
        info: { type: 'info', icon: 'fas fa-info-circle', title, message, hint }
      };
      ocrStatus.value = statusMap[type] || statusMap.error;
    };

    const handleImageUpload = async (file) => {
      if (isView.value || isEdit.value) {
        ElMessage.warning('当前模式下不允许更换图片');
        return;
      }

      isUploading.value = true;
      ocrResult.value = null;
      ocrStatus.value = null;
      imageLoadError.value = false;
      imageLoaded.value = false;
      orderForm.img_path = '';
      orderForm.img_filename = '';

      try {
        const formData = new FormData();
        formData.append('image', file.file);

        AppLogger.info('开始OCR识别:', file.file.name);
        const uploadResponse = await axios.post(`${API_BASE_URL}/api/orders/ocr-for-form/`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: APP_CONFIG.TIMEOUTS ? APP_CONFIG.TIMEOUTS.OCR_PROCESSING : 30000
        });

        if (uploadResponse.data.code === 200) {
          const ocrData = uploadResponse.data.data;
          let orderCode = ocrData.order_code || '';

          if (!orderCode || orderCode.trim() === '') {
            ocrResult.value = ocrData;
            ElMessage.error('未识别到订单编号，请重新上传清晰的订单截图');
            showOCRResult('error', '识别失败', '未识别到订单编号', '请重新上传清晰的订单截图');
            isUploading.value = false;
            return;
          }

          try {
            const response = await axios.get(`${API_BASE_URL}/api/orders/check/${orderCode}/`, {
              timeout: 10000
            });

            if (response.data.code === 200 && response.data.data.exists) {
              const existingUser = response.data.data.order.upload_user;
              ElMessage.warning(`订单编号 "${orderCode}" 已由 ${existingUser} 上传`);
              showOCRResult('warning', '订单已存在',
                `订单编号 "${orderCode}" 已存在于系统中`,
                `原上传者: ${existingUser}, 请修改订单编号或联系管理员`);
              isUploading.value = false;
              return;
            } else {
              ocrResult.value = ocrData;
              if (ocrData.img_path && ocrData.img_path.trim() !== '') {
                let serverImageUrl = ocrData.img_path;
                if (!serverImageUrl.startsWith('http')) {
                  serverImageUrl = serverImageUrl.startsWith('/')
                    ? `${API_BASE_URL}${serverImageUrl}`
                    : `${API_BASE_URL}/${serverImageUrl}`;
                }
                orderForm.img_path = serverImageUrl;
                orderForm.img_filename = ocrData.img_filename || file.file.name;
              }
              applyOCRResult();
              showOCRResult('success', '识别成功',
                `已识别到新订单 "${orderCode}"，已自动填充表单`,
                '请确认信息无误后点击"确认"按钮提交');
              isUploading.value = false;
            }
          } catch (checkError) {
            AppLogger.warn('订单检查失败:', checkError);
            if (orderCode) {
              ocrResult.value = ocrData;
              if (ocrData.img_path && ocrData.img_path.trim() !== '') {
                let serverImageUrl = ocrData.img_path;
                if (!serverImageUrl.startsWith('http')) {
                  serverImageUrl = serverImageUrl.startsWith('/')
                    ? `${API_BASE_URL}${serverImageUrl}`
                    : `${API_BASE_URL}/${serverImageUrl}`;
                }
                orderForm.img_path = serverImageUrl;
                orderForm.img_filename = ocrData.img_filename || file.file.name;
              }
              applyOCRResult();
              showOCRResult('info', '识别成功（检查服务不可用）',
                `识别到订单编号: ${orderCode}，已自动填充表单`,
                '请仔细确认信息后提交');
            }
            isUploading.value = false;
          }

        } else if (uploadResponse.data.code === 409) {
          const orderCode = uploadResponse.data.data.order_code || '未知';
          const uploader = uploadResponse.data.data.existing_uploader || '其他用户';
          ocrResult.value = uploadResponse.data.data;
          ElMessage.warning(`订单编号 "${orderCode}" 已由 ${uploader} 上传`);
          showOCRResult('warning', '订单已存在',
            `订单编号 "${orderCode}" 已由 ${uploader} 上传`,
            '请修改订单编号或取消添加操作');
          isUploading.value = false;

        } else if (uploadResponse.data.code === 400) {
          let errorMsg = uploadResponse.data.msg || '未识别到订单编号';
          ElMessage.error(errorMsg);
          showOCRResult('error', '识别失败', errorMsg, '请重新上传清晰的订单截图');
          isUploading.value = false;

        } else if (uploadResponse.data.code === 403) {
          ElMessage.error(uploadResponse.data.msg || '您没有权限上传此订单');
          showOCRResult('error', '权限不足',
            uploadResponse.data.msg || '您没有权限',
            '请使用正确的账号登录');
          isUploading.value = false;

        } else {
          let errorMessage = uploadResponse.data.msg || 'OCR识别过程出错';
          ElMessage.error(errorMessage);
          showOCRResult('error', '识别失败', errorMessage, '请重新上传或手动填写');
          isUploading.value = false;
        }

      } catch (error) {
        let errorTitle = '上传失败';
        let errorMessage = '图片上传失败，请重试';
        let errorHint = '请检查网络连接或稍后重试';

        if (error.response && error.response.data) {
          const errorData = error.response.data;
          if (errorData.msg && errorData.msg.includes('未识别到订单编号')) {
            errorTitle = '识别失败';
            errorMessage = '未识别到订单编号';
            errorHint = '请重新上传清晰的订单截图';
          } else if (errorData.code === 409) {
            const orderCode = errorData.data?.order_code || '未知';
            const uploader = errorData.data?.existing_uploader || '其他用户';
            errorTitle = '订单已存在';
            errorMessage = `订单编号 "${orderCode}" 已由 ${uploader} 上传`;
            errorHint = '请修改订单编号或联系管理员';
            if (errorData.data) ocrResult.value = errorData.data;
          } else if (errorData.code === 403) {
            errorTitle = '权限不足';
            errorMessage = '您没有权限上传订单图片';
            errorHint = '请使用普通用户账号登录';
          } else if (errorData.msg) {
            errorMessage = errorData.msg;
          }
          ElMessage.error(errorMessage);
        } else if (error.code === 'ECONNABORTED') {
          errorTitle = '上传超时';
          errorMessage = 'OCR识别超时';
          errorHint = '请稍后重试或上传更小的图片';
          ElMessage.error(errorMessage);
        } else if (error.message.includes('Network Error')) {
          errorMessage = '网络连接失败';
          errorHint = '请检查网络连接后重试';
          ElMessage.error(errorMessage);
        } else {
          ElMessage.error(error.message || '上传失败');
        }

        AppLogger.error('OCR识别失败:', error);
        showOCRResult('error', errorTitle, errorMessage, errorHint);
        isUploading.value = false;
      }
    };

    const applyOCRResult = () => {
      if (!ocrResult.value) return;
      if (!isEdit.value && !isView.value) {
        const currentUserValue = orderForm.upload_user;
        const currentImgPath = orderForm.img_path;
        const currentImgFilename = orderForm.img_filename;

        Object.keys(orderForm).forEach(key => {
          if (key !== 'id' && key !== 'img_path' && key !== 'img_filename') {
            orderForm[key] = '';
          }
        });

        orderForm.upload_user = currentUserValue || currentUser.username;
        orderForm.img_path = currentImgPath;
        orderForm.img_filename = currentImgFilename;

        let dataSource = ocrResult.value;
        if (ocrResult.value.extracted_data) {
          dataSource = ocrResult.value.extracted_data;
        } else if (ocrResult.value.data) {
          dataSource = ocrResult.value.data;
        }

        const fieldMappings = [
          // 英文映射
          { source: 'order_code', target: 'order_code', label: '订单编号' },
          { source: 'product_name', target: 'product_name', label: '商品名称' },
          { source: 'specification', target: 'specification', label: '商品规格' },
          { source: 'product_price', target: 'product_price', label: '商品价格' },
          { source: 'payment_method', target: 'payment_method', label: '支付方式' },
          { source: 'actual_amount', target: 'actual_amount', label: '实付金额' },
          { source: 'logistics_company', target: 'logistics_company', label: '物流公司' },
          { source: 'tracking_number', target: 'tracking_number', label: '快递单号' },
          { source: 'order_status', target: 'order_status', label: '订单状态' },
          { source: 'receiver', target: 'receiver', label: '收件人' },
          { source: 'contact', target: 'contact', label: '联系方式' },
          { source: 'shipping_address', target: 'shipping_address', label: '收货地址' },
          { source: 'shop_name', target: 'shop_name', label: '店铺名称' },
          { source: 'order_time', target: 'order_time', label: '下单时间' },
          { source: 'group_time', target: 'group_time', label: '拼单时间' },
          { source: 'ship_time', target: 'ship_time', label: '发货时间' },
          // 中文映射
          { source: '订单编号', target: 'order_code', label: '订单编号' },
          { source: '商品名称', target: 'product_name', label: '商品名称' },
          { source: '商品规格', target: 'specification', label: '商品规格' },
          { source: '商品价格', target: 'product_price', label: '商品价格' },
          { source: '支付方式', target: 'payment_method', label: '支付方式' },
          { source: '实付金额', target: 'actual_amount', label: '实付金额' },
          { source: '物流公司', target: 'logistics_company', label: '物流公司' },
          { source: '快递单号', target: 'tracking_number', label: '快递单号' },
          { source: '订单状态', target: 'order_status', label: '订单状态' },
          { source: '收件人', target: 'receiver', label: '收件人' },
          { source: '联系方式', target: 'contact', label: '联系方式' },
          { source: '收货地址', target: 'shipping_address', label: '收货地址' },
          { source: '店铺名称', target: 'shop_name', label: '店铺名称' },
          { source: '下单时间', target: 'order_time', label: '下单时间' },
          { source: '拼单时间', target: 'group_time', label: '拼单时间' },
          { source: '发货时间', target: 'ship_time', label: '发货时间' }
        ];

        let filledFields = 0;
        fieldMappings.forEach(mapping => {
          const value = dataSource[mapping.source];
          if (value !== undefined && value !== null && value.toString().trim() !== '') {
            orderForm[mapping.target] = value.toString().trim();
            filledFields++;
          }
        });

        if (!orderForm.order_status || orderForm.order_status.trim() === '') {
          if (orderForm.payment_method && orderForm.payment_method.includes('已付')) {
            orderForm.order_status = '已付款';
          } else if (orderForm.tracking_number && orderForm.tracking_number.trim() !== '') {
            orderForm.order_status = '已发货';
          } else {
            orderForm.order_status = '待付款';
          }
        }

        if (!orderForm.upload_user || orderForm.upload_user.trim() === '') {
          orderForm.upload_user = currentUser.username;
        }

        if (filledFields > 0) {
          ElMessage.success(`已自动填充 ${filledFields} 个字段`);
          AppLogger.debug('OCR自动填充字段数:', filledFields);
        }
      } else if (isEdit.value) {
        ElMessage.info('编辑模式下，请手动参考OCR识别结果进行修改');
      }
    };

    // ==================== 提交订单表单 ====================
    const submitCustomOrderForm = async () => {
      if (!orderForm.order_code || orderForm.order_code.trim() === '') {
        ElMessage.error('订单编号不能为空');
        return;
      }

      if (!orderForm.product_name || orderForm.product_name.trim() === '') {
        ElMessage.error('商品名称不能为空');
        return;
      }

      if (!isEdit.value && !isView.value) {
        if (!orderForm.img_path || orderForm.img_path.trim() === '') {
          ElMessage.warning('请先上传订单截图进行OCR识别');
          return;
        }
      }

      try {
        let response;
        const orderData = {
          ...orderForm,
          id: isEdit.value ? orderForm.id : null
        };

        if (!orderData.upload_user || orderData.upload_user.trim() === '') {
          orderData.upload_user = currentUser.username;
        }

        if (!isEdit.value) {
          try {
            const checkResponse = await axios.get(`${API_BASE_URL}/api/orders/check/${orderData.order_code}/`);
            if (checkResponse.data.code === 200 && checkResponse.data.data.exists) {
              ElMessage.error(`订单编号 "${orderData.order_code}" 已存在，无法重复添加`);
              return;
            }
          } catch (checkError) {
            AppLogger.warn('订单检查失败，继续保存:', checkError);
          }
        }

        AppLogger.info(`${isEdit.value ? '更新' : '添加'}订单:`, orderData.order_code);
        if (isEdit.value) {
          response = await axios.post(`${API_BASE_URL}/api/orders/update/`, orderData);
        } else {
          response = await axios.post(`${API_BASE_URL}/api/orders/add/`, orderData);
        }

        if (response.data.code === 200) {
          await loadOrders();
          closeDialogForm();
          ElMessage.success(isEdit.value ? '订单更新成功' : '订单添加成功');
          AppLogger.info(`${isEdit.value ? '更新' : '添加'}订单成功:`, orderData.order_code);
          ocrResult.value = null;
          ocrStatus.value = null;
        } else if (response.data.code === 409) {
          ElMessage.error(`订单编号 "${orderForm.order_code}" 已存在，无法重复添加`);
          orderForm.order_code = '';
        } else {
          let errorMsg = response.data.msg || '保存失败';
          if (errorMsg.includes('unexpected keyword argument')) {
            errorMsg = '字段格式错误，请联系管理员';
          }
          ElMessage.error(errorMsg);
          AppLogger.error('保存订单失败:', errorMsg);
        }
      } catch (error) {
        let errorMsg = '保存失败';
        if (error.response && error.response.data) {
          errorMsg = error.response.data.msg || JSON.stringify(error.response.data);
          if (errorMsg.includes('unexpected keyword argument')) {
            errorMsg = '字段格式错误，请联系管理员';
          }
        } else if (error.message) {
          errorMsg = error.message;
        }

        AppLogger.error('保存订单异常:', error);
        ElMessage.error(`保存失败: ${errorMsg}`);
      }
    };

    // ==================== 分页方法 ====================
    const handleSizeChange = (size) => {
      pageSize.value = size;
      currentPage.value = 1;
      getPageOrders();
    };

    const handleCurrentChange = (page) => {
      currentPage.value = page;
      getPageOrders();
    };

    // ==================== 生命周期 ====================
    onMounted(async () => {
      // 生产环境安全检查 - 暂时注释掉强制HTTPS
      const isLocalDev = window.location.hostname === 'localhost' ||
        window.location.hostname === '127.0.0.1';

      if (!isLocalDev) {
        // 暂时注释掉强制 HTTPS，因为使用 IP 地址
        // if (window.location.protocol === 'http:') {
        //   window.location.href = window.location.href.replace('http:', 'https:');
        //   return;
        // }

        // 禁用右键菜单和开发者工具（可选）
        document.addEventListener('contextmenu', e => e.preventDefault());
        document.addEventListener('keydown', e => {
          if (e.key === 'F12' || (e.ctrlKey && e.shiftKey && e.key === 'I') || (e.ctrlKey && e.key === 'U')) {
            e.preventDefault();
          }
        });
      }

      // 从localStorage获取记住的用户名
      const rememberedUser = localStorage.getItem('rememberedUser');
      if (rememberedUser) {
        loginForm.username = rememberedUser;
        loginForm.remember = true;
      }

      // 添加窗口大小变化监听
      window.addEventListener('resize', handleResize);

      // ==================== 检查认证状态 ====================
      async function safeCheckAuth() {
        try {
          const response = await axios.get(`${API_BASE_URL}/api/check-auth/`, {
            timeout: 10000
          });

          if (response.data.code === 200 && response.data.data.authenticated) {
            const user = response.data.data.user;
            currentUser.username = user.username;

            currentUser.is_superuser = user.is_superuser;
            currentUser.user_type_name = user.is_superuser ? '超级用户' : '普通用户';

            if (user.is_superuser) {
              isLoginSuccess.value = true;
              await loadOrders();
              AppLogger.info('超级用户登录成功，加载订单数据');
              showMobileTips(); // 显示移动端提示
            } else {
              if (window.location.pathname === '/' || window.location.pathname === '/index.html') {
                window.location.href = '/upload.html';
              }
            }
          } else {
            loginForm.password = '';
            registerForm.password = '';
            registerForm.checkPassword = '';
            AppLogger.debug('用户未登录');
          }
        } catch (error) {
          AppLogger.error('检查登录状态失败:', error);
          loginForm.password = '';
        }
      }

      await safeCheckAuth();
      AppLogger.info('应用初始化完成');
    });

    // ==================== 返回所有属性和方法 ====================
    return {
      // 状态
      isLoginSuccess, isRegisterMode, currentUser, mobileMenuOpen,
      loginForm, loginErrors, registerForm, registerErrors,
      orders, pageOrders, searchKeyword, selectedOrders,
      currentPage, pageSize, total, dateRange, activeIndex,
      dialogVisible, isView, isEdit, dialogTitle, isUploading,
      ocrResult, ocrStatus, imageLoadError, exportLoading, imageLoaded,
      orderForm,

      // 方法
      submitLogin, submitRegister, logout, showForgotPassword,
      formatDate, formatDateForExport, handleSearch, handleDateChange,
      handleClearSearch, searchOrders, getAllOrders, handleSelectionChange,
      showAddDialog, viewOrder, editOrder, deleteOrder, batchDelete,
      closeDialogForm, beforeImageUpload, handleImageUpload,
      applyOCRResult, submitCustomOrderForm, handleSizeChange,
      handleCurrentChange, handleImageError, handleImageLoad,
      exportToExcel, toggleMobileMenu, handleMobileMenuItemClick
    };
  }
});

// 使用 Element Plus
app.use(ElementPlus);

// 挂载应用
app.mount('#app');

// 全局错误处理
window.addEventListener('error', (event) => {
  AppLogger.error('全局错误:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
  AppLogger.error('未处理的Promise拒绝:', event.reason);
});

// 监听页面可见性变化，用于移动端优化
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') {
    // 页面被隐藏时清理一些资源
    const loadingInstances = document.querySelectorAll('.el-loading-mask');
    loadingInstances.forEach(instance => {
      if (instance.parentNode) {
        instance.parentNode.removeChild(instance);
      }
    });
  }
});