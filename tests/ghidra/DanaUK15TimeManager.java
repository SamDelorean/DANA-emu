// @category Dana
// Read-only-project analysis of original Palm Time Manager; output stays private.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.app.decompiler.*;
import java.io.*;
import java.util.*;
public class DanaUK15TimeManager extends GhidraScript {
 public void run() throws Exception {
  PrintWriter out=new PrintWriter(new FileWriter(getScriptArgs()[0]));
  out.println("PROGRAM "+currentProgram.getName()+" LANGUAGE "+currentProgram.getLanguageID());
  DecompInterface decomp=new DecompInterface();decomp.openProgram(currentProgram);
  long[][] ranges={{0x1007fc60L,0x100800a8L},{0x10080178L,0x100801a4L}};
  LinkedHashSet<Function> funcs=new LinkedHashSet<>();
  for(long[] range:ranges){
   for(long pc=range[0];pc<range[1];){
    Address a=toAddr(pc);Instruction ins=getInstructionAt(a);
    if(ins==null){disassemble(a);ins=getInstructionAt(a);}
    if(ins==null){pc+=2;continue;}
    out.printf("%08X %s",pc,ins.toString());
    if(ins.getMnemonicString().equalsIgnoreCase("trap")){
     out.printf(" PALM_TRAP=%04X",getShort(a.add(2))&65535);
    }
    out.println();
    if(ins.getMnemonicString().equalsIgnoreCase("link.w")||ins.getMnemonicString().equalsIgnoreCase("link")){
     Function f=getFunctionAt(a);if(f==null)try{f=createFunction(a,null);}catch(Exception e){}
     if(f!=null)funcs.add(f);
    }
    pc+=ins.getLength();if(ins.getMnemonicString().equalsIgnoreCase("trap"))pc+=2;
   }
  }
  for(Function f:funcs){
   out.println("DECOMPILE "+f.getEntryPoint()+" "+f.getName());
   DecompileResults result=decomp.decompileFunction(f,30,monitor);
   if(result.decompileCompleted())out.println(result.getDecompiledFunction().getC());else out.println(result.getErrorMessage());
  }
  decomp.dispose();out.close();
 }
}