export interface PageQuery {
  page?: number;
  size?: number;
  sort?: string;
  q?: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  hasNext: boolean;
}
