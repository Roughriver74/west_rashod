import { useState, useEffect } from 'react'

/**
 * Hook to detect if screen is mobile size
 * @param breakpoint - Max width for mobile (default: 768px)
 */
export function useIsMobile(breakpoint: number = 768): boolean {
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia(`(max-width: ${breakpoint}px)`)

    const handleChange = (e: MediaQueryListEvent | MediaQueryList) => {
      setIsMobile(e.matches)
    }

    // Set initial value
    handleChange(mediaQuery)

    // Add listener
    mediaQuery.addEventListener('change', handleChange)

    return () => {
      mediaQuery.removeEventListener('change', handleChange)
    }
  }, [breakpoint])

  return isMobile
}

/**
 * Hook to detect if screen is small (tablet or smaller)
 * @param breakpoint - Max width for small screen (default: 992px)
 */
export function useIsSmallScreen(breakpoint: number = 992): boolean {
  const [isSmallScreen, setIsSmallScreen] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia(`(max-width: ${breakpoint}px)`)

    const handleChange = (e: MediaQueryListEvent | MediaQueryList) => {
      setIsSmallScreen(e.matches)
    }

    // Set initial value
    handleChange(mediaQuery)

    // Add listener
    mediaQuery.addEventListener('change', handleChange)

    return () => {
      mediaQuery.removeEventListener('change', handleChange)
    }
  }, [breakpoint])

  return isSmallScreen
}

/**
 * Generic hook for custom media queries
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia(query)

    const handleChange = (e: MediaQueryListEvent | MediaQueryList) => {
      setMatches(e.matches)
    }

    // Set initial value
    handleChange(mediaQuery)

    // Add listener
    mediaQuery.addEventListener('change', handleChange)

    return () => {
      mediaQuery.removeEventListener('change', handleChange)
    }
  }, [query])

  return matches
}
