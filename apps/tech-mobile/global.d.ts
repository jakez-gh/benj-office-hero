// minimal ambient definitions to allow tests to compile without @types/jest

declare global {
  namespace jest {
    function mock(moduleName: string, factory?: any): void;
    function spyOn(object: any, method: string): any;
    function fn(): any;
    interface Matchers<R> {
      toBeTruthy(): R;
      toHaveBeenCalled(): R;
      toHaveBeenCalledWith(...args: any[]): R;
    }
  }

  const describe: (desc: string, fn: () => void) => void;
  const it: (desc: string, fn: () => void) => void;
  const expect: any;
}

export {};
