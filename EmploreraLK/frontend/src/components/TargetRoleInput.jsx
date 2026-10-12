import { TARGET_ROLE_SUGGESTIONS } from './targetRoles.js'

function TargetRoleInput({ id, value, onChange, className, required = false }) {
  return (
    <>
      <input
        id={id}
        type="text"
        list="target-role-suggestions"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Choose a suggested role or type your own"
        autoComplete="off"
        required={required}
        className={className}
      />
      <datalist id="target-role-suggestions">
        {TARGET_ROLE_SUGGESTIONS.map((role) => <option key={role} value={role} />)}
      </datalist>
    </>
  )
}

export default TargetRoleInput
