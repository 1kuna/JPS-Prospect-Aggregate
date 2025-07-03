import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'

// Simple test to verify setup
describe('Testing Setup', () => {
  it('should render a simple component', () => {
    const TestComponent = () => <div>Hello Test</div>
    render(<TestComponent />)
    expect(screen.getByText('Hello Test')).toBeInTheDocument()
  })

  it('should support basic assertions', () => {
    expect(1 + 1).toBe(2)
    expect([1, 2, 3]).toContain(2)
  })
})