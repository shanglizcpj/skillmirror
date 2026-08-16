import axios from 'axios'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('skillmirror-token')

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

http.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (!error.response) {
      error.userMessage =
        'Unable to connect to the server. Please check whether the backend is running.'
    } else if (error.response.status === 404) {
      error.userMessage = 'The requested resource was not found.'
    } else if (error.response.status >= 500) {
      error.userMessage = 'The server encountered an error. Please try again later.'
    } else {
      error.userMessage =
        error.response.data?.message || 'The request could not be completed.'
    }

    return Promise.reject(error)
  }
)

export default http