package main

import (
	"fmt"
	"viperforge/console"
	"viperforge/core"
)

func main() {
	fmt.Println(`
    ____   ____.__                     ___________                           
    \   \ /   /|__|_____   ___________ \_   _____/__________  ____   ____  
     \   Y   / |  \____ \_/ __ \_  __ \ |    __)/  _ \_  __ \/ ___\_/ __ \ 
      \     /  |  |  |_> >  ___/|  | \/ |     \(  <_> )  | \/ /_/  >  ___/ 
       \___/   |__|   __/ \___  >__|    \___  / \____/|__|  \___  / \___  >
                  |__|        \/            \/             /_____/      \/	v1.1.0-beta
                                Red Team Exploit Factory
	`)

	core.PostGenerateHook = InjectDependencyCheck
	session := core.NewSession()
	console.StartShell(session)
}
