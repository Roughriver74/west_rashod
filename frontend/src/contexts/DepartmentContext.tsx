import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getDepartments, Department } from '../api/departments'
import { useAuth } from './AuthContext'

interface DepartmentContextType {
  departments: Department[]
  selectedDepartment: Department | null
  setSelectedDepartment: (dept: Department | null) => void
  isLoading: boolean
}

const DepartmentContext = createContext<DepartmentContextType | undefined>(undefined)

export function DepartmentProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated, user } = useAuth()
  const [selectedDepartment, setSelectedDepartment] = useState<Department | null>(null)

  const { data: departments = [], isLoading } = useQuery({
    queryKey: ['departments'],
    queryFn: getDepartments,
    enabled: isAuthenticated,
  })

  // Auto-select user's department or first available
  useEffect(() => {
    if (departments.length > 0 && !selectedDepartment) {
      if (user?.department_id) {
        const userDept = departments.find((d) => d.id === user.department_id)
        if (userDept) {
          setSelectedDepartment(userDept)
          return
        }
      }
      setSelectedDepartment(departments[0])
    }
  }, [departments, user, selectedDepartment])

  return (
    <DepartmentContext.Provider
      value={{
        departments,
        selectedDepartment,
        setSelectedDepartment,
        isLoading,
      }}
    >
      {children}
    </DepartmentContext.Provider>
  )
}

export function useDepartment() {
  const context = useContext(DepartmentContext)
  if (context === undefined) {
    throw new Error('useDepartment must be used within a DepartmentProvider')
  }
  return context
}
