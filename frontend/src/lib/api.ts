const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const defaultHeaders = {
      'Content-Type': 'application/json',
    };

    const config: RequestInit = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed for ${endpoint}:`, error);
      throw error;
    }
  }

  // Document Analysis APIs
  async extractDocumentStructure(documentText: string) {
    return this.request('/api/extract-document-structure', {
      method: 'POST',
      body: JSON.stringify({ documentText }),
    });
  }

  async checkSectionSequence(sections: string[]) {
    return this.request('/api/check-section-sequence', {
      method: 'POST',
      body: JSON.stringify({ sections }),
    });
  }

  // Citation Analysis API
  async analyzeCitations(data: {
    paper_text?: string;
    paper_file?: File;
    target_journal?: string;
    analysis_type?: string;
    custom_requirements?: string;
  }) {
    const formData = new FormData();
    
    if (data.paper_text) {
      formData.append('paper_text', data.paper_text);
    }
    if (data.paper_file) {
      formData.append('paper_file', data.paper_file);
    }
    if (data.target_journal) {
      formData.append('target_journal', data.target_journal);
    }
    if (data.analysis_type) {
      formData.append('analysis_type', data.analysis_type);
    }
    if (data.custom_requirements) {
      formData.append('custom_requirements', data.custom_requirements);
    }

    return this.request('/analyze_citations', {
      method: 'POST',
      headers: {}, // Remove Content-Type to let browser set it for FormData
      body: formData,
    });
  }

  // Paper Analyzer APIs
  async analyzePaper(file: File) {
    const formData = new FormData();
    formData.append('paper_file', file);

    return this.request('/api/analyze-paper', {
      method: 'POST',
      headers: {},
      body: formData,
    });
  }

  async runTool(analysisId: string, toolName: string, toolConfig: any = {}) {
    return this.request(`/api/run-tool/${toolName}`, {
      method: 'POST',
      body: JSON.stringify({
        analysis_id: analysisId,
        tool_config: toolConfig,
      }),
    });
  }

  async getAnalysisStatus(analysisId: string) {
    return this.request(`/api/analysis-status/${analysisId}`);
  }

  // Health check
  async healthCheck() {
    return this.request('/api/health');
  }
}

export const apiClient = new ApiClient();
